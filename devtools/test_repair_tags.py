"""Tests for repair_tags in core.text_builder."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.text_builder import repair_tags


def test_translated_tags_restored():
    # Tag names translated into Thai should be restored from English
    th = "ตัวละครที่มีเครื่องหมาย <<ICO_ภารกิจGiver>> ในแผนที่ จะมีภารกิจให้ทำ"
    en = "Characters marked with <<ICO_QuestGiver>> on the map will give you new quests."
    assert repair_tags(th, en) == "ตัวละครที่มีเครื่องหมาย <<ICO_QuestGiver>> ในแผนที่ จะมีภารกิจให้ทำ"

    th = "<br><<สมบัติ_แผนที่_น้ำตก>>"
    en = "<br><<tresure_map_waterfall>>"
    assert repair_tags(th, en) == "<br><<tresure_map_waterfall>>"

    th = "กด <<หยุด>> เพื่อหยุดม้าของคุณ"
    en = "Hold <<Stop>> to stop your horse."
    assert repair_tags(th, en) == "กด <<Stop>> เพื่อหยุดม้าของคุณ"


def test_spaced_tags_and_multi_tags():
    # Multiple tags with Thai words and spaces (Issue #22 example: 1076662)
    th = "เลือกระเบิดโดยใช้ << เมาส์ >> และกด << IK_LeftMouse >> เพื่อให้ใช้งานได้"
    en = "Select a bomb using <<Mouse>> and press <<IK_LeftMouse>> to make it active."
    assert repair_tags(th, en) == "เลือกระเบิดโดยใช้ <<Mouse>> และกด <<IK_LeftMouse>> เพื่อให้ใช้งานได้"


def test_html_closing_tags():
    # </ i>, </ b>, </ font>, < /font>, </font >, </I>
    assert repair_tags("ข้อความ <i>เอียง</ i> ปกติ") == "ข้อความ <i>เอียง</i> ปกติ"
    assert repair_tags("ข้อความ <b>หนา</ b> ปกติ") == "ข้อความ <b>หนา</b> ปกติ"
    assert repair_tags("ข้อความ <font color=\"#CD7D03\">สี</ font> ปกติ") == "ข้อความ <font color=\"#CD7D03\">สี</font> ปกติ"
    assert repair_tags("ข้อความ <font color=\"#CD7D03\">สี< /font> ปกติ") == "ข้อความ <font color=\"#CD7D03\">สี</font> ปกติ"
    assert repair_tags("ข้อความ <i>เอียง</I> ปกติ") == "ข้อความ <i>เอียง</i> ปกติ"


def test_html_color_tags():
    # Spaced hex, spaced attribute, malformed tag names
    assert repair_tags('<font color = "# CD7D03">ข้อความ</font>') == '<font color="#CD7D03">ข้อความ</font>'
    assert repair_tags('<font color = " # CD7D03 ">ข้อความ</font>') == '<font color="#CD7D03">ข้อความ</font>'
    assert repair_tags('<font color ="#CD7D03">ข้อความ</font>') == '<font color="#CD7D03">ข้อความ</font>'
    assert repair_tags('<aFed = "# CD7D03">ข้อความ</font>') == '<font color="#CD7D03">ข้อความ</font>'
    assert repair_tags('<href = "color =" # CD7D03 ">ข้อความ</font>') == '<font color="#CD7D03">ข้อความ</font>'


def test_bracket_variations():
    # Spaces between angle brackets: < < or > >
    th = "ภารกิจที่มีเครื่องหมาย < <ICO_EP1Quest >> ใน Journal"
    en = "Quests marked with <<ICO_EP1Quest>> in Journal"
    assert repair_tags(th, en) == "ภารกิจที่มีเครื่องหมาย <<ICO_EP1Quest>> ใน Journal"

    # Single angle bracket promoted when matching English tag
    th = "กด <CiriSpecialAttack> ค้างไว้"
    en = "Hold <<CiriSpecialAttack>> to attack"
    assert repair_tags(th, en) == "กด <<CiriSpecialAttack>> ค้างไว้"

    # One missing bracket <Tag>> or <<Tag>
    th = "กระดาษ <q301_drawing_crib>> ที่เด็กวาด"
    en = "Paper <<q301_drawing_crib>> drawn by a child"
    assert repair_tags(th, en) == "กระดาษ <<q301_drawing_crib>> ที่เด็กวาด"


def test_mismatched_counts_strip_whitespace():
    # If tag counts don't match, strip internal whitespace without corrupting
    th = "กด << IK_LeftMouse >> หรือคลิกขวา"
    en = "Press the button or right click"
    assert repair_tags(th, en) == "กด <<IK_LeftMouse>> หรือคลิกขวา"


def test_intact_text():
    # Regular text without tags remains untouched
    assert repair_tags("ข้อความภาษาไทยธรรมดา ไม่มีแท็ก") == "ข้อความภาษาไทยธรรมดา ไม่มีแท็ก"
    assert repair_tags("") == ""


if __name__ == "__main__":
    test_translated_tags_restored()
    test_spaced_tags_and_multi_tags()
    test_html_closing_tags()
    test_html_color_tags()
    test_bracket_variations()
    test_mismatched_counts_strip_whitespace()
    test_intact_text()
    print("All repair_tags tests passed!")
