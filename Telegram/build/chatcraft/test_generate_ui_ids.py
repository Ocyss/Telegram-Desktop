import importlib.util
import tempfile
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "ui_ids", Path(__file__).with_name("generate-ui-ids.py")
)
GEN = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GEN)


class ScannerTests(unittest.TestCase):
    def scan(self, body):
        return GEN.scan("void Build(SectionBuilder &builder) {" + body + "}")

    def test_all_control_sinks(self):
        for method in GEN.METHODS:
            with self.subTest(method=method):
                self.assertEqual(
                    self.scan(
                        "builder."
                        + method
                        + '({.id = u"stable/control"_q, .title = f(a, b)});'
                    ),
                    {"stable/control"},
                )

    def test_reject_business_comments_strings_empty_and_dynamic(self):
        self.assertEqual(
            self.scan("""
            Business data{.id = u"business/id"_q};
            other.addButton({.id = u"business/button"_q});
            // builder.addButton({.id = u"comment"_q});
            /* builder.addCheckbox({.id = u"comment2"_q}); */
            auto text = "builder.addButton({.id = fake});";
            builder.addButton({.id = u""_q});
            builder.addButton({.id = peer.id()});
            object->setObjectName(u"unconnected"_q);
        """),
            set(),
        )

    def test_lambda_forwarding_and_scopes(self):
        source = """
            void One(SectionBuilder &builder) {
                const auto add = [&](QString id, QString title) {
                    builder.addCheckbox({.id = std::move(id), .title = title});
                };
                add(u"one/control"_q, u"not-an-id"_q);
            }
            void Two(SectionBuilder &builder) {
                const auto add = [&](QString title, QString id) {
                    builder.addButton({.id = id, .title = title});
                };
                add(u"not-an-id"_q, u"two/control"_q);
            }
        """
        self.assertEqual(GEN.scan(source), {"one/control", "two/control"})

    def test_receiver_names_do_not_leak_between_functions(self):
        source = """
            void Real(SectionBuilder &builder) {
                builder.addButton({.id = u"real"_q});
            }
            void Other(Business &builder) {
                builder.addButton({.id = u"fake"_q});
                builder.add([] { return widget(); }, [] {
                    return SearchEntry{.id = u"fake/custom"_q};
                });
            }
        """
        self.assertEqual(GEN.scan(source), {"real"})
        self.assertEqual(
            GEN.scan(
                source[source.index("void Other") :]
                + source[: source.index("void Other")]
            ),
            {"real"},
        )

    def test_receiver_prototypes_and_default_lambda_parameters(self):
        source = """
            void Declared(SectionBuilder &builder);
            void Other(Business &builder) {
                builder.addButton({.id = u"fake/prototype"_q});
            }
            void Real(Settings::Builder::SectionBuilder *builder) {
                const auto wrong = [&](Business &builder = business) {
                    builder.addButton({.id = u"fake/default"_q});
                };
                wrong();
                builder->addButton({.id = u"real/pointer"_q});
            }
        """
        self.assertEqual(GEN.scan(source), {"real/pointer"})

    def test_receiver_shadowing_in_lambda_and_local_block(self):
        self.assertEqual(
            self.scan("""
            builder.addCheckbox({.id = u"outer/before"_q});
            const auto wrong = [&](Business &builder) {
                builder.addButton({.id = u"fake/lambda"_q});
            };
            wrong(business);
            {
                Business &builder = business;
                builder.addButton({.id = u"fake/block"_q});
                const auto add = [&](QString id) {
                    builder.addButton({.id = id});
                };
                add(u"fake/forwarded"_q);
            }
            const auto add = [&](QString id) {
                builder.addButton({.id = id});
            };
            add(u"real/forwarded"_q);
            builder.addButton({.id = u"outer/after"_q});
        """),
            {"outer/before", "outer/after", "real/forwarded"},
        )

    def test_builder_parameter_in_nested_lambda_is_local(self):
        source = """
            void Other(Business &builder) {
                const auto build = [&](SectionBuilder &builder) {
                    builder.addButton({.id = u"real/lambda"_q});
                };
                builder.addButton({.id = u"fake"_q});
            }
        """
        self.assertEqual(GEN.scan(source), {"real/lambda"})

    def test_char_literals_and_disabled_unbalanced_code(self):
        self.assertEqual(
            self.scan("""
            auto brace = '{';
            auto quote = '\\"';
#if 0
            if (disabled) {
                builder.addButton({.id = u"disabled"_q});
#endif
            builder.addButton({.id = u"enabled"_q});
        """),
            {"enabled"},
        )

    def test_search_only_entries_not_listed(self):
        self.assertEqual(
            self.scan("""
            builder.add(nullptr, [] { return SearchEntry{.id = u"search-only"_q}; });
            auto entry = SearchEntry{.id = u"detached"_q};
            builder.add([](const WidgetContext &ctx) { return makeWidget(ctx); },
                [] { return SearchEntry{.id = u"connected"_q}; });
        """),
            {"connected"},
        )

    def test_main_menu_only_connected_action_argument(self):
        self.assertEqual(
            GEN.scan(
                """
            checkHighlightControl(u"main-menu/unconnected"_q, widget);
            addAction(tr::title(), { &st::icon }, u"main-menu/connected"_q);
            addAction(tr::title(), { &st::icon });
        """,
                True,
            ),
            {"main-menu/connected"},
        )

    def test_generation_deterministic_and_source_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "settings").mkdir()
            (root / "window").mkdir()
            menu = root / "window/window_main_menu.cpp"
            menu.write_text(
                'addAction(title(), {}, u"main-menu/test"_q);', encoding="utf-8"
            )
            source = root / "settings/control.cpp"
            source.write_text(
                'void B(SectionBuilder &builder) { builder.addButton({.id = u"z"_q}); }',
                encoding="utf-8",
            )
            output = root / "gen/ids.inc"
            GEN.generate(root, output)
            first = output.read_bytes()
            stamp = output.stat().st_mtime_ns
            GEN.generate(root, output)
            self.assertEqual(output.stat().st_mtime_ns, stamp)
            self.assertEqual(output.read_bytes(), first)
            source.write_text(
                'void B(SectionBuilder &builder) { builder.addCheckbox({.id = u"a"_q}); }',
                encoding="utf-8",
            )
            GEN.generate(root, output)
            self.assertIn(b'u"a"_q', output.read_bytes())
            self.assertNotIn(b'u"z"_q', output.read_bytes())
            extra = root / "settings/extra.cpp"
            extra.write_text(
                'void B(SectionBuilder &builder) { builder.addControl({.id = u"extra"_q}); }',
                encoding="utf-8",
            )
            GEN.generate(root, output)
            self.assertIn(b'u"extra"_q', output.read_bytes())
            extra.unlink()
            source.unlink()
            GEN.generate(root, output)
            self.assertNotIn(b'u"a"_q', output.read_bytes())
            self.assertNotIn(b'u"extra"_q', output.read_bytes())

    def test_repository_catalog(self):
        root = Path(__file__).resolve().parents[2] / "SourceFiles"
        ids = GEN.collect(root)
        self.assertEqual(ids, sorted(set(ids)))
        for value in (
            "main/profile",
            "advanced/auto_download_private",
            "advanced/title_chat_name",
            "main-menu/night-mode",
        ):
            self.assertIn(value, ids)
        self.assertNotIn("sessions/current", ids)


if __name__ == "__main__":
    unittest.main()
