from services.preprocessing.text_normalizer import normalize_text


def test_markup_is_stripped_but_content_and_maths_are_kept():
    assert normalize_text("Use <b>REST</b> APIs.<script>alert(1)</script> Done") == "Use REST APIs. Done"
    assert normalize_text("if a < b and x <= 3 then ok") == "if a < b and x <= 3 then ok"
    assert normalize_text("<p>one</p><p>two</p>") == "one two"
