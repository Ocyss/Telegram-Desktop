#pragma once

#include "settings/settings_type.h"

#include <QtCore/QJsonObject>
#include <QtCore/QStringList>

namespace Chatcraft {

[[nodiscard]] bool Enabled();
[[nodiscard]] QJsonObject GetSettings();
[[nodiscard]] bool SetValue(const QString &key, QJsonValue value);
[[nodiscard]] bool ResetSettings();
[[nodiscard]] QString LastError();
[[nodiscard]] bool HideSponsored();
[[nodiscard]] bool HideGroupedChats();
[[nodiscard]] bool HideChat(bool mainList, bool inCustomFolder);
[[nodiscard]] QStringList UiIds();
[[nodiscard]] bool UiVisible(const QString &id);
[[nodiscard]] bool SetUiVisible(const QString &id, bool visible);
[[nodiscard]] rpl::producer<bool> UiVisibleValue(QString id);
[[nodiscard]] rpl::producer<> SettingsChanges();
[[nodiscard]] Settings::Type SettingsId();

} // namespace Chatcraft
