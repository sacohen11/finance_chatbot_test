import unittest

from logic import build_assistant_response


class TestChartRecommendation(unittest.TestCase):
    def test_time_series_line_chart(self):
        response = build_assistant_response("show monthly trend")
        self.assertIn("chart_spec", response)
        self.assertEqual(response["chart_spec"]["data"][0]["type"], "scatter")

    def test_category_bar_chart(self):
        response = build_assistant_response("compare categories")
        self.assertEqual(response["chart_spec"]["data"][0]["type"], "bar")

    def test_budget_stacked_bar_chart(self):
        response = build_assistant_response("budget vs actual by department")
        self.assertEqual(response["chart_spec"]["layout"]["barmode"], "stack")

    def test_budget_share_pie_chart(self):
        response = build_assistant_response("actual spend share by department")
        self.assertEqual(response["chart_spec"]["data"][0]["type"], "pie")


if __name__ == "__main__":
    unittest.main()
