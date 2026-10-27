# Chatcraft UI ID catalog

`generate-ui-ids.py` writes only a build-directory include. CMake runs it before
Telegram compilation when `CHATCRAFT_ENABLED` is enabled. Source edits and generator
edits invalidate the timestamp; `CONFIGURE_DEPENDS` and a generated source-list
manifest also invalidate it when source files are added or removed. An unchanged
catalog is not rewritten. Non-Chatcraft builds do not require this generated file.

The scanner recognizes inline argument aggregates on `SectionBuilder` control
methods, and search entries supplied to `builder.add` with a widget factory.
Same-file local lambda calls can forward literal IDs directly or through
`std::move`. The main-menu catalog comes from the ID argument of its existing
visibility-connected `addAction` calls, not from highlight-only registrations.
Empty IDs, arbitrary business `.id` fields, and search-only entries are excluded.
The shared builder insertion point wraps widgets without changing the returned
widget pointer or removing native `shown` scopes. Subsection titles use a scope.

This is a bounded source scanner, not a C++ compiler: computed IDs, external
helper forwarding, constexpr aliases, separately assembled argument structures,
macros and arbitrary C++ string expressions are not resolved. It scans all
platform branches, so some entries apply only on other platforms. It does not
promise to enumerate every runtime control.

`objectName` widgets are intentionally not cataloged: their native show/hide
state machines have no common composable visibility producer here. Globally
forcing visibility could expose natively hidden widgets or interfere with error,
overlay and pre-launch windows. Non-widget QObject names must not become UI IDs.
Supporting these widgets requires explicit, individually verified visibility
seams; merely listing their names would not implement hiding.

Run the scanner tests from the desktop fork root:

```
python -B Telegram/build/chatcraft/test_generate_ui_ids.py
```

These tests validate scanning and generated content, not C++ compilation, CMake
build scheduling or interactive widget behavior.
