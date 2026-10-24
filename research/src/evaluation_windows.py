"""Current evaluation boundaries; these dates do not change trading rules."""
PREPARATION = ('2014-11-07', '2019-12-31')
PERIODS = {
    'history_2020_2023': ('2020-01-01', '2023-12-31'),
    'history_2024_2026Sep18': ('2024-01-01', '2026-09-18'),
    'history_combined': ('2020-01-01', '2026-09-18'),
    'recent_month_test': ('2026-09-19', '2026-10-19'),
    'course_october_partial': ('2026-10-01', '2026-10-19'),
}
LABELS = {
    'history_2020_2023': '历史回测 A',
    'history_2024_2026Sep18': '历史回测 B',
    'history_combined': '历史合并期（A+B）',
    'recent_month_test': '最近一个月历史测试',
    'course_october_partial': '课程十月阶段性评价',
}
TEST = 'recent_month_test'
COURSE = 'course_october_partial'
STATUS = ('Retrospective historical evaluation after strategy development; '
          'not an untouched prospective test. October is partial, not the full course test.')
