"""Structural C++ target inspection must ignore literals and comments."""

import unittest

from tools.target_inspector import inspect_target, tokenize_cpp_executable


class TargetInspectorTests(unittest.TestCase):
    def test_comment_markers_inside_strings_do_not_hide_executable_violations(self):
        target = r'''int main() { std::cout << "/*"; std::cout << "//";
            if (1 && 1) goto bad; return 0; }'''
        codes = {issue.code for issue in inspect_target(target)}
        self.assertIn("TARGET-PROHIBITED-BOOLEAN", codes)
        self.assertIn("TARGET-DANGLING-GOTO", codes)

    def test_escaped_quotes_raw_literals_and_spliced_comments_remain_data(self):
        target = r'''int main() {
            std::cout << "\" // else &&";
            std::cout << R"mine(/* else || #x */)mine";
            // ignored \
            else not || #x
            return 0;
        }'''
        self.assertEqual(inspect_target(target), ())

    def test_valid_target_ignores_preprocessor_string_and_comments(self):
        target = r'''#include <iostream>
int main() {
    std::cout << "else not || ! #x"; // else && !
    /* goto spl_lbl_1; spl_lbl_1: ; */
    return 0;
}
'''
        self.assertEqual(inspect_target(target), ())

    def test_string_literal_and_comment_words_are_not_executable_tokens(self):
        tokens = tokenize_cpp_executable('int main() { std::cout << "else not"; /* || ! */ return 0; }')
        values = [token.value for token in tokens]
        self.assertNotIn("else", values)
        self.assertNotIn("not", values)
        self.assertNotIn("||", values)
        self.assertNotIn("!", values)

    def test_duplicate_and_dangling_labels_are_reported(self):
        target = "int main() { goto spl_lbl_2; spl_lbl_1: ; spl_lbl_1: ; return 0; }"
        codes = {issue.code for issue in inspect_target(target)}
        self.assertIn("TARGET-DUPLICATE-LABEL", codes)
        self.assertIn("TARGET-DANGLING-GOTO", codes)

    def test_undeclared_generated_storage_is_reported(self):
        target = "int main() { std::cout << spl_tmp_19; return 0; }"
        codes = {issue.code for issue in inspect_target(target)}
        self.assertIn("TARGET-UNDECLARED-STORAGE", codes)

    def test_undeclared_parameter_storage_is_reported(self):
        target = "int main() { std::cout << spl_p12; return 0; }"
        codes = {issue.code for issue in inspect_target(target)}
        self.assertIn("TARGET-UNDECLARED-STORAGE", codes)

    def test_raw_spl_identifier_is_rejected(self):
        target = "int main() { int spl_v1{}; spl_v1 = #x; return 0; }"
        codes = {issue.code for issue in inspect_target(target)}
        self.assertIn("TARGET-RAW-SPL-NAME", codes)

    def test_raw_spl_name_at_start_of_line_is_not_a_preprocessor_directive(self):
        codes = {issue.code for issue in inspect_target("int main() {\n #x = 1;\n return 0; }")}
        self.assertIn("TARGET-RAW-SPL-NAME", codes)

    def test_prohibited_control_vocabulary_is_rejected(self):
        target = "int main() { if (true && false) goto L; L: ; return 0; }"
        codes = {issue.code for issue in inspect_target(target)}
        self.assertIn("TARGET-PROHIBITED-BOOLEAN", codes)

    def test_runtime_spl_function_call_is_rejected(self):
        target = "int main() { spl_f12(3); return 0; }"
        codes = {issue.code for issue in inspect_target(target)}
        self.assertIn("TARGET-RUNTIME-SPL-CALL", codes)

    def test_multiple_main_and_nonterminal_return_are_reported(self):
        target = "int main() { return 0; } int main() { return 0; }"
        codes = {issue.code for issue in inspect_target(target)}
        self.assertIn("TARGET-MAIN-COUNT", codes)
        self.assertIn("TARGET-RETURN-COUNT", codes)


if __name__ == "__main__":
    unittest.main()
