import json
from typing import Optional, Union, List
from typing import List, get_args, get_origin
from pydantic import BaseModel


class PydanticUtils:    
    @staticmethod
    def is_type_of_list(data_type: type):
        origin_type = get_origin(data_type)
        return origin_type == list or origin_type == List
    
    #获取字段类型
    @staticmethod
    def get_field_type(model: BaseModel, field_name: str):
        type = model.__annotations__.get(field_name, None)
        native_type = PydanticUtils.get_native_type(type)
        return native_type
    
    #获取原生类型
    @staticmethod
    def get_native_type(optional_type):
        if hasattr(optional_type, '__origin__') and optional_type.__origin__ is Union:
            args = optional_type.__args__
            native_types = [arg for arg in args if arg is not type(None)]
            if native_types:
                return native_types[0]
        return optional_type
        
    @staticmethod
    def merge_object(*, source_obj: Optional[BaseModel], dest_obj: Optional[BaseModel], merge_fields: list[str] = None, deep_merge_fields: list[str] = None) -> Optional[BaseModel]:
        """
            source_obj : source object for merging
            dest_obj : target object for merging
            merge_fields : merge based on designated fields
            deep_merge_fields : fields requiring deep merge(only one level deep)
        """
        if dest_obj is None:
            return source_obj
        if source_obj is None:
            return dest_obj
        if not isinstance(source_obj, type(dest_obj)):
            return None
        
        for field_name in (merge_fields or source_obj.__dict__.keys()):
            if hasattr(source_obj, field_name):
                source_value = getattr(source_obj, field_name)
                if source_value is not None:
                    if deep_merge_fields and field_name in deep_merge_fields and isinstance(source_value, BaseModel):
                        dest_value = getattr(dest_obj, field_name, None)
                        merged_value = PydanticUtils.merge_object(source_obj=source_value, dest_obj=dest_value)
                        setattr(dest_obj, field_name, merged_value)
                    else:
                        setattr(dest_obj, field_name, source_value)
        
        return dest_obj
        