from typing import Self

from fanzadl.models.video.base import (
    _SkeletonLibraryItemContentsModel,
)


class UnavailableLibraryItemContentsModel(_SkeletonLibraryItemContentsModel):
    @classmethod
    def from_contents_model(cls, model: _SkeletonLibraryItemContentsModel) -> Self:
        field_data = {k: v for k, v in model.__dict__.items() if k in cls.model_fields}
        instance = cls.model_construct(**field_data)

        # Copy private attributes
        # ruff: disable[SLF001]
        instance._get_authorization = model._get_authorization
        instance._get_exploit_id = model._get_exploit_id
        instance._rotate_tokens = model._rotate_tokens
        instance._max_rotation_retries = model._max_rotation_retries
        instance._javstash_api_key = model._javstash_api_key
        # ruff: enable[SLF001]

        return instance
