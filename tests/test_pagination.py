from survey_builder.domain.pagination import Pagination


def test_first_page_defaults():
    p = Pagination.from_request(None, total=100, per_page=25)
    assert (p.page, p.pages, p.offset) == (1, 4, 0)
    assert not p.has_prev and p.has_next


def test_page_is_clamped():
    assert Pagination.from_request("99", total=50, per_page=25).page == 2
    assert Pagination.from_request("-3", total=50, per_page=25).page == 1
    assert Pagination.from_request("abc", total=50, per_page=25).page == 1


def test_empty_list_has_one_page():
    p = Pagination.from_request("1", total=0)
    assert p.pages == 1
    assert not p.has_next


def test_offset_of_later_pages():
    p = Pagination.from_request("3", total=75, per_page=25)
    assert p.offset == 50
    assert p.has_prev and not p.has_next
