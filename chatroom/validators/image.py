from dataclasses import dataclass

from django.core.validators import BaseValidator
from django.db import models
from django.utils.deconstruct import deconstructible


@deconstructible
class MaxFileSizeValidator(BaseValidator):
    message = f"ファイルサイズが上限を超えています"
    code = "max_file_size"

    def compare(self, a:int, b:int) -> bool:
        return a > b

    def clean(self, x: models.fields.files.FieldFile) -> int:
        return x.size


@deconstructible
@dataclass
class WidthHeight:
    width: int
    height: int


@deconstructible
class ImageAspectRatioValidator(BaseValidator):
    message = f""
    code = ""

    def compare(self, a: WidthHeight, b: WidthHeight) -> bool:
        """
        多少の誤差は許容
        """
        return a.width * b.height - a.height * b.width > 10

    def clean(self, x: models.fields.files.ImageFieldFile) -> WidthHeight:
        return WidthHeight(width=x.width, height=x.height)