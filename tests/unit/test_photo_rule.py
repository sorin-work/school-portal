from school_portal.photos import family_may_see


def test_no_consent_means_not_even_the_own_family():
    assert not family_may_see("none", [])


def test_own_family_sees_a_photo_of_their_child_alone():
    assert family_may_see("own", [])
    assert family_may_see("group", [])


def test_a_group_photo_needs_group_consent_from_everyone_else():
    assert family_may_see("own", ["group", "group"])
    assert not family_may_see("group", ["group", "own"])
    assert not family_may_see("group", ["none"])
