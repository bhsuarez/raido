from app.services.metadata_extractor import MetadataExtractor as ME


def test_parse_filename_various_forms():
    # 01 - Artist - Title
    md = ME._parse_filename("01 - The Band - The Song")
    assert md["track_number"] == 1
    assert md["filename_artist"] == "The Band"
    assert md["title"] == "The Song"

    # Artist - Title
    md = ME._parse_filename("Artist - A Very Long Song Title")
    assert md["title"] == "A Very Long Song Title"

    # 01 Title
    md = ME._parse_filename("07 Space Odyssey")
    assert md["track_number"] == 7
    assert md["title"] == "Space Odyssey"

    # 03. Title
    md = ME._parse_filename("03. Intro (Remastered)")
    assert md["track_number"] == 3
    assert md["title"].startswith("Intro")


def test_clean_path_component_and_filename_part():
    assert ME._clean_path_component("[2020] Rock  Classics (Deluxe)") == "Rock Classics"
    assert ME._clean_filename_part("Song_Title_[Prod. By X] (feat. Y)") == "Song Title"


def test_normalize_metadata_year_and_numbers():
    md = {"year": "2023-01-01", "track_number": "10/12", "disc_number": "2/3", "bpm": "129.7"}
    out = ME._normalize_metadata(md)
    assert out["year"] == 2023
    assert out["track_number"] == 10
    assert out["disc_number"] == 2
    assert out["bpm"] == 130


def test_looks_like_genre():
    assert ME._looks_like_genre("Rock") is True
    assert ME._looks_like_genre("ObscureGenreName") is False

