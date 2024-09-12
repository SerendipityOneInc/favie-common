import unittest
from pydantic import BaseModel
from typing import List
from favie_common.bigtable.bigtable_utils import BigtableUtils  # 请确保导入正确

class TestModel(BaseModel):
    name: str
    age: int
    is_active: bool
    scores: List[float]

class TestNestedModel(BaseModel):
    id: int
    test_model: TestModel

class TestBigtableRepository(unittest.TestCase):


    def test_pydantic_field_convert_str(self):
        # 测试原生类型
        self.assertEqual(BigtableUtils.pydantic_field_convert_str(10), "10")
        self.assertEqual(BigtableUtils.pydantic_field_convert_str(10.5), "10.5")
        self.assertEqual(BigtableUtils.pydantic_field_convert_str("test"), "test")
        self.assertEqual(BigtableUtils.pydantic_field_convert_str(True), "True")

        # 测试 Pydantic 模型
        model = TestModel(name="John", age=30, is_active=True, scores=[9.5, 8.0])
        expected_json = '{"name":"John","age":30,"is_active":true,"scores":[9.5,8.0]}'
        self.assertEqual(BigtableUtils.pydantic_field_convert_str(model), expected_json)

        # 测试列表
        self.assertEqual(BigtableUtils.pydantic_field_convert_str([1, 2, 3]), "[1, 2, 3]")
        
        # 测试嵌套模型
        nested_model = TestNestedModel(id=1, test_model=model)
        expected_nested_json = '{"id":1,"test_model":{"name":"John","age":30,"is_active":true,"scores":[9.5,8.0]}}'
        self.assertEqual(BigtableUtils.pydantic_field_convert_str(nested_model), expected_nested_json)

        # 测试不支持的类型
        with self.assertRaises(TypeError):
            BigtableUtils.pydantic_field_convert_str(set([1, 2, 3]))

    def test_str_convert_pydantic_field(self):
        # 测试原生类型
        self.assertEqual(BigtableUtils.str_convert_pydantic_field("10", int), 10)
        self.assertEqual(BigtableUtils.str_convert_pydantic_field("10.5", float), 10.5)
        self.assertEqual(BigtableUtils.str_convert_pydantic_field("test", str), "test")
        self.assertEqual(BigtableUtils.str_convert_pydantic_field("true", bool), True)

        # 测试列表
        self.assertEqual(
            BigtableUtils.str_convert_pydantic_field("[9.5, 8.0]", List[float]),
            [9.5, 8.0]
        )

        # 测试 Pydantic 模型
        json_str = '{"name": "John", "age": 30, "is_active": true, "scores": [9.5, 8.0]}'
        model = BigtableUtils.str_convert_pydantic_field(json_str, TestModel)
        self.assertIsInstance(model, TestModel)
        self.assertEqual(model.name, "John")
        self.assertEqual(model.age, 30)
        self.assertEqual(model.is_active, True)
        self.assertEqual(model.scores, [9.5, 8.0])

        # 测试嵌套模型
        nested_json_str = '{"id": 1, "test_model": {"name": "John", "age": 30, "is_active": true, "scores": [9.5, 8.0]}}'
        nested_model = BigtableUtils.str_convert_pydantic_field(nested_json_str, TestNestedModel)
        self.assertIsInstance(nested_model, TestNestedModel)
        self.assertEqual(nested_model.id, 1)
        self.assertIsInstance(nested_model.test_model, TestModel)
        self.assertEqual(nested_model.test_model.name, "John")

        # 测试不支持的类型
        with self.assertRaises(TypeError):
            BigtableUtils.str_convert_pydantic_field("test", set)

if __name__ == '__main__':
    unittest.main()