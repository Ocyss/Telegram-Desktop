#include "chatcraft/chatcraft_chat_list.h"

#include "chatcraft/chatcraft_settings.h"
#include "data/data_chat_filters.h"
#include "data/data_session.h"
#include "history/history.h"
#include "main/main_session.h"

namespace Chatcraft {

ChatList::ChatList(not_null<Main::Session*> session)
: _session(session)
, _visible(Dialogs::SortMode::Date) {
}

Dialogs::IndexedList *ChatList::show(
		Dialogs::IndexedList *source,
		bool mainList) {
	if (mainList && HideGroupedChats()) {
		_source = source;
		return &_visible;
	}
	if (_source) {
		_source = nullptr;
		while (!_visible.empty()) {
			_visible.remove((*_visible.begin())->key());
		}
	}
	return source;
}

bool ChatList::visible(Dialogs::Key key) const {
	if (!_source || !_source->contains(key)) {
		return false;
	}
	const auto history = key.history();
	if (!history) {
		return true;
	}
	const auto &filters = _session->data().chatsFilters().list();
	const auto grouped = ranges::any_of(filters, [&](const auto &filter) {
		return filter.id() != 0 && filter.contains(history);
	});
	return !HideChat(true, grouped);
}

ChatList::Change ChatList::update(Dialogs::Key key, float64 narrowRatio) {
	auto result = Change();
	if (!_source) {
		return result;
	}
	const auto before = _visible.getRow(key);
	if (before) {
		result.moved.from = before->top();
		result.moved.height = before->height();
	}
	if (!visible(key)) {
		if (before) {
			_visible.remove(key);
			result.existenceChanged = true;
		}
		return result;
	}
	const auto links = _visible.addToEnd(key, false);
	_visible.adjustByDate(links);
	const auto heightChanged = _visible.updateHeight(key, narrowRatio);
	result.moved.to = links.main->top();
	result.moved.height = links.main->height();
	result.existenceChanged = !before || heightChanged;
	return result;
}

bool ChatList::sync(float64 narrowRatio) {
	if (!_source) {
		return false;
	}
	auto removed = std::vector<Dialogs::Key>();
	for (const auto row : _visible) {
		if (!_source->contains(row->key())) {
			removed.push_back(row->key());
		}
	}
	auto changed = !removed.empty();
	for (const auto key : removed) {
		_visible.remove(key);
	}
	for (const auto row : *_source) {
		if (update(row->key(), narrowRatio)) {
			changed = true;
		}
	}
	return changed;
}

} // namespace Chatcraft
