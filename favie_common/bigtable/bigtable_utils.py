import json
from typing import get_args
from pydantic import BaseModel

from favie_common.common.pydantic_utils import PydanticUtils


class BigtableUtils:
    @staticmethod    
    def pydantic_field_convert_str(param,force_dump_json :bool = False) -> str:
        if isinstance(param, (int, float, str, bool)):  # 原生对象
            return json.dumps(param) if force_dump_json else str(param)
        elif isinstance(param, BaseModel):  # Pydantic 对象
            return param.model_dump_json(exclude_none=True)
        elif isinstance(param, list):  # 列表
            json_strings = [BigtableUtils.pydantic_field_convert_str(item,True) for item in param]  # 递归处理列表中的每个
            return '[' + ', '.join(json_strings) + ']'  # 组合成一个合法的 JSON 字符串元素
        else:
            raise TypeError(f"Unsupported type : {type(param)}")

    @staticmethod
    def str_convert_pydantic_field(string_data: str, data_type: type):        
        # 处理原生类型
        if data_type == int:
            return int(string_data)
        elif data_type == float:
            return float(string_data)
        elif data_type == str:
            return string_data
        elif data_type == bool:
            return string_data.lower() == "true"
            
        # 处理列表类型 必须先处理列表类型，因为列表类型是泛型
        if PydanticUtils.is_type_of_list(data_type):
            item_type = get_args(data_type)[0]
            items = json.loads(string_data)
            return [BigtableUtils.str_convert_pydantic_field(item, item_type) for item in items]
        
        # 处理 Pydantic 对象
        if issubclass(data_type, BaseModel):
            if isinstance(string_data, str):
                return data_type.model_validate_json(string_data)
            elif isinstance(string_data, dict):
                return data_type(**string_data)
        
        raise TypeError(f"Unsupported type: {data_type}")    
