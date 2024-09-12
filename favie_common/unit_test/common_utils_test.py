import unittest
from datetime import datetime, timedelta
from favie_common.common.common_utils import CommonUtils  

class TestCommonUtils(unittest.TestCase):

    def test_all_not_none(self):
        self.assertTrue(CommonUtils.all_not_none(1, "a", []))
        self.assertFalse(CommonUtils.all_not_none(1, None, "a"))

    def test_any_none(self):
        self.assertTrue(CommonUtils.any_none(1, None, "a"))
        self.assertFalse(CommonUtils.any_none(1, "a", []))
        
    def test_any_not_none(self):
        self.assertTrue(CommonUtils.any_not_none(1, None, "a"))
        self.assertFalse(CommonUtils.any_not_none(None, None, None))

    def test_all_none(self):
        self.assertTrue(CommonUtils.all_none(None, None, None))
        self.assertFalse(CommonUtils.all_none(None, 1, None))

    def test_host_trip_www(self):
        self.assertEqual(CommonUtils.host_trip_www("www.example.com"), "example.com")
        self.assertEqual(CommonUtils.host_trip_www("example.com"), "example.com")
        self.assertIsNone(CommonUtils.host_trip_www(None))

    def test_md5_hash(self):
        self.assertEqual(CommonUtils.md5_hash("test"), "098f6bcd4621d373cade4e832627b4f6")

    def test_list_len(self):
        self.assertEqual(CommonUtils.list_len([1, 2, 3]), 3)
        self.assertEqual(CommonUtils.list_len([]), 0)
        self.assertEqual(CommonUtils.list_len(None), 0)

    def test_is_empty(self):
        self.assertTrue(CommonUtils.is_empty([]))
        self.assertTrue(CommonUtils.is_empty({}))
        self.assertTrue(CommonUtils.is_empty(set()))
        self.assertTrue(CommonUtils.is_empty(""))
        self.assertFalse(CommonUtils.is_empty([1]))
        self.assertFalse(CommonUtils.is_empty({"a": 1}))
        self.assertFalse(CommonUtils.is_empty({1}))
        self.assertFalse(CommonUtils.is_empty("a"))
        with self.assertRaises(TypeError):
            CommonUtils.is_empty(42)

    def test_current_timestamp(self):
        now = datetime.now().timestamp()
        result = CommonUtils.current_timestamp()
        self.assertAlmostEqual(result, now, delta=1)  # 允许1秒的误差

    def test_divide_chunks(self):
        lst = [1, 2, 3, 4, 5, 6, 7, 8, 9]
        result = CommonUtils.divide_chunks(lst, 3)
        self.assertEqual(result, [[1, 2, 3], [4, 5, 6], [7, 8, 9]])

    def test_get_hostname(self):
        self.assertEqual(CommonUtils.get_hostname("https://www.example.com/path"), "www.example.com")
        self.assertEqual(CommonUtils.get_hostname("http://example.com"), "example.com")

    def test_get_domain(self):
        self.assertEqual(CommonUtils.get_domain("https://www.example.co.uk/path"), "example.co.uk")
        self.assertEqual(CommonUtils.get_domain("http://sub.example.com"), "example.com")

    def test_get_sub_domain(self):
        self.assertEqual(CommonUtils.get_sub_domain("https://www.example.com/path"), "www")
        self.assertEqual(CommonUtils.get_sub_domain("http://sub.example.com"), "sub")
        self.assertEqual(CommonUtils.get_sub_domain("http://example.com"), "")

    def test_get_full_subdomain(self):
        self.assertEqual(CommonUtils.get_full_subdomain("https://www.example.com/path"), "www.example.com")
        self.assertEqual(CommonUtils.get_full_subdomain("http://sub.example.com"), "sub.example.com")

if __name__ == '__main__':
    unittest.main()