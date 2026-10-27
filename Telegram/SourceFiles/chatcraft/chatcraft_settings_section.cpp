#include "chatcraft/chatcraft_settings.h"

#include "lang/lang_keys.h"
#include "settings/settings_common_session.h"
#include "styles/style_settings.h"
#include "ui/boxes/confirm_box.h"
#include "ui/widgets/checkbox.h"
#include "ui/wrap/vertical_layout.h"
#include "window/window_session_controller.h"
#include "ui/widgets/fields/input_field.h"
#include "ui/wrap/slide_wrap.h"
#include "styles/style_widgets.h"
#include "ui/vertical_list.h"
#include "ui/ui_utility.h"
#include "ui/widgets/buttons.h"
#include "ui/widgets/scroll_area.h"

namespace Chatcraft {
namespace {

class Advanced final : public Settings::Section<Advanced> {
public:
	Advanced(
		QWidget *parent,
		not_null<Window::SessionController*> controller)
	: Section(parent, controller) {
		const auto content = Ui::CreateChild<Ui::VerticalLayout>(this);
		const auto error = [=] {
			controller->show(Ui::MakeInformBox(rpl::single(LastError())));
		};
		const auto toggle = [&](QString key, Fn<bool()> current) {
			const auto checkbox = content->add(object_ptr<Ui::Checkbox>(
				content,
				key,
				current(),
				st::settingsCheckbox), st::settingsCheckboxPadding);
			checkbox->checkedChanges() | rpl::on_next([=](bool checked) {
				if (checked != current() && !SetValue(key, checked)) {
					checkbox->setChecked(current());
					error();
				}
			}, checkbox->lifetime());
			SettingsChanges() | rpl::on_next([=] {
				checkbox->setChecked(current());
			}, checkbox->lifetime());
		};
		toggle(u"hide_grouped_chats"_q, [] { return HideGroupedChats(); });
		toggle(u"hide_sponsored"_q, [] { return HideSponsored(); });

		Ui::AddSubsectionTitle(content, tr::lng_community_visibility_visible());
		const auto search = content->add(object_ptr<Ui::InputField>(
			content,
			st::defaultInputField,
			tr::lng_dlg_filter()), st::settingsCheckboxPadding);
		const auto listHeight = search->height() * 6;
		const auto listContainer = content->add(
			object_ptr<Ui::RpWidget>(content));
		listContainer->setFixedHeight(listHeight);
		const auto scroll = Ui::CreateChild<Ui::ScrollArea>(listContainer);
		const auto rows = scroll->setOwnedWidget(
			object_ptr<Ui::VerticalLayout>(scroll));
		listContainer->widthValue() | rpl::on_next([=](int width) {
			scroll->setGeometry(0, 0, width, listHeight);
			rows->resizeToWidth(width);
		}, scroll->lifetime());
		scroll->show();
		for (const auto &id : UiIds()) {
			const auto wrap = rows->add(
				object_ptr<Ui::SlideWrap<Ui::Checkbox>>(
					rows,
					object_ptr<Ui::Checkbox>(
						rows, id, UiVisible(id), st::settingsCheckbox),
					st::settingsCheckboxPadding));
			const auto checkbox = wrap->entity();
			wrap->toggleOn(rpl::single(true) | rpl::then(
				search->changes() | rpl::map([=] {
					return id.contains(search->getLastText().trimmed(),
						Qt::CaseInsensitive);
				})));
			wrap->finishAnimating();
			checkbox->checkedChanges() | rpl::on_next([=](bool checked) {
				if (checked != UiVisible(id) && !SetUiVisible(id, checked)) {
					checkbox->setChecked(UiVisible(id));
					error();
				}
			}, checkbox->lifetime());
			UiVisibleValue(id) | rpl::on_next([=](bool visible) {
				checkbox->setChecked(visible);
			}, checkbox->lifetime());
		}
		Settings::AddButtonWithIcon(
			content,
			tr::lng_settings_experimental_restore(),
			st::settingsButtonNoIcon
		)->setClickedCallback([=] {
			if (!ResetSettings()) {
				error();
			}
		});
		Ui::ResizeFitChild(this, content);
		if (!LastError().isEmpty()) {
			error();
		}
	}

	rpl::producer<QString> title() override {
		return rpl::single(u"Chatcraft"_q);
	}

};

} // namespace

Settings::Type SettingsId() {
	return Advanced::Id();
}

} // namespace Chatcraft
