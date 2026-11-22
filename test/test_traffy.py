from processing.traffy import clean_traffy

OK = {"ticket_id": "A", "coords": "100.5,13.7", "timestamp": "2022-02-21 22:34:56",
      "star": "4.0", "duration_minutes_total": "680", "problemtype_tag": "{ภัยทางถนน}", "photo": ""}


def reasons(*rows):
    return [why for _, why in clean_traffy(list(rows)).rejected]


def test_good_row_is_cast():
    g = clean_traffy([OK]).good[0]
    assert (g.star, g.duration_minutes_total, g.photo, g.problemtype_tag) == (4.0, 680, None, ["ภัยทางถนน"])
    assert g.lon_lat == (100.5, 13.7)


def test_bad_rows_are_rejected_with_reason():
    assert reasons({**OK, "timestamp": "not a date"}) == ["bad timestamp: 'not a date'"]
    assert reasons({**OK, "coords": ""}) == ["missing coords"]
    assert reasons({**OK, "coords": "abc"}) == ["malformed coords"]
    assert reasons({**OK, "star": "9"}) == ["star out of range"]
    assert reasons({**OK, "duration_minutes_total": "-5"}) == ["negative duration"]
    assert reasons({**OK, "ticket_id": ""}) == ["missing ticket_id"]


def test_duplicate_ticket_id_first_wins():
    res = clean_traffy([OK, {**OK, "comment": "later"}])
    assert len(res.good) == 1 and res.good[0].comment is None
    assert [why for _, why in res.rejected] == ["duplicate ticket_id"]
