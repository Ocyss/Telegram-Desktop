#include "chatcraft/chatcraft_settings.h"

#include "settings.h"
#include <QtCore/QCoreApplication>
#include <QtCore/QJsonArray>
#include <QtCore/QJsonDocument>
#include <QtCore/QThread>

#ifdef CHATCRAFT_ENABLED
extern "C" {
void *chatcraft_settings_open(const char *directory);
void chatcraft_settings_free(void *handle);
char *chatcraft_settings_get_json(void *handle);
bool chatcraft_settings_set_json(void *handle, const char *json);
char *chatcraft_settings_last_error(void *handle);
bool chatcraft_settings_ui_visible(void *handle, const char *id);
bool chatcraft_settings_hide_sponsored(void *handle);
bool chatcraft_settings_chat_list_hide(
	void *handle, bool enabled, uint32_t mode, bool in_custom_folder);
void chatcraft_string_free(char *text);
}
#endif // CHATCRAFT_ENABLED

namespace Chatcraft {
namespace {

class Store final {
public:
	Store() {
#ifdef CHATCRAFT_ENABLED
		const auto directory = (cWorkingDir() + u"tdata/chatcraft"_q).toUtf8();
		handle = chatcraft_settings_open(directory.constData());
#endif // CHATCRAFT_ENABLED
	}
	~Store() {
#ifdef CHATCRAFT_ENABLED
		chatcraft_settings_free(handle);
#endif // CHATCRAFT_ENABLED
	}

	void *handle = nullptr;
	rpl::event_stream<> changes;
	QString error;

};

Store &SettingsStore() {
	Expects(QCoreApplication::instance() != nullptr);
	Expects(QThread::currentThread() == QCoreApplication::instance()->thread());
	static auto result = Store();
	return result;
}

#ifdef CHATCRAFT_ENABLED
QString TakeString(char *text) {
	if (!text) {
		return QString();
	}
	const auto result = QString::fromUtf8(text);
	chatcraft_string_free(text);
	return result;
}
#endif // CHATCRAFT_ENABLED

bool Save(QJsonObject object) {
	auto &store = SettingsStore();
#ifdef CHATCRAFT_ENABLED
	if (store.handle) {
		const auto json = QJsonDocument(object).toJson(QJsonDocument::Compact);
		if (chatcraft_settings_set_json(store.handle, json.constData())) {
			store.error.clear();
			store.changes.fire({});
			return true;
		}
		store.error = TakeString(chatcraft_settings_last_error(store.handle));
		return false;
	}
#endif // CHATCRAFT_ENABLED
	store.error = u"Chatcraft settings are unavailable."_q;
	return false;
}

} // namespace

bool Enabled() {
#ifdef CHATCRAFT_ENABLED
	return true;
#else
	return false;
#endif // CHATCRAFT_ENABLED
}

QJsonObject GetSettings() {
	auto &store = SettingsStore();
#ifdef CHATCRAFT_ENABLED
	if (store.handle) {
		const auto raw = TakeString(chatcraft_settings_get_json(store.handle));
		const auto document = QJsonDocument::fromJson(raw.toUtf8());
		if (document.isObject()) {
			return document.object();
		}
		store.error = u"Invalid Chatcraft settings JSON."_q;
		return {};
	}
#endif // CHATCRAFT_ENABLED
	store.error = u"Chatcraft settings are unavailable."_q;
	return {};
}

bool SetValue(const QString &key, QJsonValue value) {
	auto object = GetSettings();
	if (object.isEmpty()) {
		return false;
	}
	object.insert(key, value);
	return Save(std::move(object));
}

bool ResetSettings() {
	auto object = GetSettings();
	if (object.isEmpty()) {
		return false;
	}
	object.insert(u"version"_q, 1);
	object.insert(u"hide_grouped_chats"_q, false);
	object.insert(u"read_first"_q, false);
	object.insert(u"hide_sponsored"_q, true);
	object.insert(u"hidden_ui_ids"_q, QJsonArray());
	return Save(std::move(object));
}

QString LastError() {
	auto &store = SettingsStore();
#ifdef CHATCRAFT_ENABLED
	if (store.error.isEmpty() && store.handle) {
		return TakeString(chatcraft_settings_last_error(store.handle));
	}
#endif // CHATCRAFT_ENABLED
	return store.error;
}

bool HideSponsored() {
#ifdef CHATCRAFT_ENABLED
	const auto handle = SettingsStore().handle;
	return handle && chatcraft_settings_hide_sponsored(handle);
#else
	return false;
#endif // CHATCRAFT_ENABLED
}

bool HideGroupedChats() {
#ifdef CHATCRAFT_ENABLED
	const auto handle = SettingsStore().handle;
	return handle && chatcraft_settings_chat_list_hide(handle, true, 0, true);
#else
	return false;
#endif // CHATCRAFT_ENABLED
}

bool HideChat(bool mainList, bool inCustomFolder) {
#ifdef CHATCRAFT_ENABLED
	const auto handle = SettingsStore().handle;
	return handle && chatcraft_settings_chat_list_hide(
		handle, true, mainList ? 0 : 2, inCustomFolder);
#else
	return false;
#endif // CHATCRAFT_ENABLED
}

QStringList UiIds() {
	return {
		u"main/profile"_q,
		u"main/notifications"_q,
		u"main/privacy"_q,
		u"main/chat"_q,
		u"main/folders"_q,
		u"main/advanced"_q,
		u"main/devices"_q,
		u"main/power"_q,
		u"main/language"_q,
		u"main/currency"_q,
		u"main/business"_q,
		u"main/send-gift"_q,
		u"main/faq"_q,
		u"main/features"_q,
		u"main/ask-question"_q,
		u"main-menu/create-group"_q,
		u"main-menu/create-channel"_q,
		u"main-menu/contacts"_q,
		u"main-menu/calls"_q,
		u"main-menu/saved-messages"_q,
		u"main-menu/settings"_q,
		u"main-menu/night-mode"_q,
	};
}

bool UiVisible(const QString &id) {
	if (!UiIds().contains(id)) {
		return true;
	}
#ifdef CHATCRAFT_ENABLED
	const auto handle = SettingsStore().handle;
	const auto utf8 = id.toUtf8();
	return !handle || chatcraft_settings_ui_visible(handle, utf8.constData());
#else
	return true;
#endif // CHATCRAFT_ENABLED
}

bool SetUiVisible(const QString &id, bool visible) {
	if (!UiIds().contains(id)) {
		return false;
	}
	auto object = GetSettings();
	if (object.isEmpty()) {
		return false;
	}
	const auto old = object.value(u"hidden_ui_ids"_q).toArray();
	auto ids = QJsonArray();
	for (const auto &value : old) {
		if (value.toString() != id) {
			ids.append(value);
		}
	}
	if (!visible) {
		ids.append(id);
	}
	object.insert(u"hidden_ui_ids"_q, ids);
	return Save(std::move(object));
}

rpl::producer<> SettingsChanges() {
	return SettingsStore().changes.events();
}

rpl::producer<bool> UiVisibleValue(QString id) {
	return rpl::single(UiVisible(id)) | rpl::then(
		SettingsChanges() | rpl::map([=] { return UiVisible(id); })
	) | rpl::distinct_until_changed();
}

} // namespace Chatcraft
