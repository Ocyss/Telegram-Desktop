#pragma once

#include "dialogs/dialogs_common.h"
#include "dialogs/dialogs_indexed_list.h"

namespace Main {
class Session;
} // namespace Main

namespace Chatcraft {

class ChatList final {
public:
	explicit ChatList(not_null<Main::Session*> session);

	struct Change {
		Dialogs::PositionChange moved;
		bool existenceChanged = false;
		explicit operator bool() const {
			return existenceChanged || moved.from != moved.to;
		}
	};

	[[nodiscard]] Dialogs::IndexedList *show(
		Dialogs::IndexedList *source,
		bool mainList);
	[[nodiscard]] bool active() const { return _source != nullptr; }
	[[nodiscard]] Change update(Dialogs::Key key, float64 narrowRatio);
	bool sync(float64 narrowRatio);

private:
	[[nodiscard]] bool visible(Dialogs::Key key) const;

	const not_null<Main::Session*> _session;
	Dialogs::IndexedList *_source = nullptr;
	Dialogs::IndexedList _visible;

};

} // namespace Chatcraft
