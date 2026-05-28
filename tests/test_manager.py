from collections.abc import Generator

import pytest
from pytest_mock import MockerFixture

from fanzadl.manager import FanzaDLManager
from fanzadl.models.library import LibraryDataModel, LibraryItemModel
from fanzadl.models.video import UnavailableLibraryItemContentsModel
from fanzadl.models.video.video import VideoLibraryItemContentsModel


def _make_spoofed_item(mylibrary_id: int) -> VideoLibraryItemContentsModel:
    item = VideoLibraryItemContentsModel.model_construct(mylibrary_id=mylibrary_id)
    item.__pydantic_private__.update(  # type: ignore[union-attr]
        {
            "_get_authorization": lambda: "Bearer dummy",
            "_get_exploit_id": lambda: "uid:dummy",
            "_rotate_tokens": None,
            "_max_rotation_retries": 0,
            "_javstash_api_key": None,
        }
    )
    return item


@pytest.fixture
def manager(mocker: MockerFixture) -> FanzaDLManager:
    def _fake_process_auth(self, **_kwargs) -> None:  # noqa: ANN001
        self.user_id = "test_user"
        self.refresh_token = "test_refresh"
        self.access_token = "test_access"

    mocker.patch.object(FanzaDLManager, "_process_auth_input", _fake_process_auth)
    return FanzaDLManager(
        email="x@example.com",
        password="password",
        auto_populate_library=False,
        track_expired_items=True,
    )


def test_update_library_expires_removed_item(
    manager: FanzaDLManager,
    mocker: MockerFixture,
) -> None:
    spoofed_a = _make_spoofed_item(11111)  # will be absent from API response
    spoofed_b = _make_spoofed_item(22222)  # will be present in API response

    manager.library = {11111: spoofed_a, 22222: spoofed_b}

    # Build a fake library page containing only item B
    fake_item = LibraryItemModel.model_construct(
        contents={"mylibrary_id": 22222, "shop_name": "videoa"}
    )
    fake_page = LibraryDataModel.model_construct(
        content_total=1,
        list_=[fake_item],
    )

    def _fake_generator(self) -> Generator[LibraryDataModel]:  # noqa: ANN001
        yield fake_page

    mocker.patch.object(FanzaDLManager, "_user_library_generator", _fake_generator)
    mocker.patch(
        "fanzadl.manager.library_item_adapter.validate_python",
        return_value=spoofed_b,
    )

    manager.update_library()

    # Item B is retained in library
    assert manager.library == {22222: spoofed_b}
    assert 22222 not in manager.expired_library

    # Item A has been moved to expired_library as UnavailableLibraryItemContentsModel
    assert 11111 in manager.expired_library
    expired = manager.expired_library[11111]
    assert isinstance(expired, UnavailableLibraryItemContentsModel)
    assert expired.mylibrary_id == 11111
