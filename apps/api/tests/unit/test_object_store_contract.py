from __future__ import annotations

from io import BytesIO
from unittest.mock import Mock

from camcat.services.object_store import ObjectStore


def test_transient_lifecycle_is_merged_without_erasing_operator_rules() -> None:
    store = object.__new__(ObjectStore)
    store.bucket = "camcat"
    store._client = Mock()
    store._client.list_buckets.return_value = {"Buckets": [{"Name": "camcat"}]}
    store._client.get_bucket_lifecycle_configuration.return_value = {
        "Rules": [
            {
                "ID": "operator-archive-rule",
                "Status": "Enabled",
                "Filter": {"Prefix": "archive/"},
                "Expiration": {"Days": 30},
            }
        ]
    }

    store.ensure_bucket()

    configuration = store._client.put_bucket_lifecycle_configuration.call_args.kwargs[
        "LifecycleConfiguration"
    ]
    assert [rule["ID"] for rule in configuration["Rules"]] == [
        "operator-archive-rule",
        "expire-transient-user-media",
    ]


def test_stream_upload_can_record_short_lived_staging_metadata() -> None:
    store = object.__new__(ObjectStore)
    store.bucket = "camcat"
    store._client = Mock()
    stream = BytesIO(b"video")

    store.upload_stream(
        stream,
        "temporary/provider-staging/id/source.mp4",
        "video/mp4",
        metadata={"kind": "provider-staging", "expires-at": "soon"},
    )

    assert store._client.upload_fileobj.call_args.kwargs["ExtraArgs"] == {
        "ContentType": "video/mp4",
        "Metadata": {"kind": "provider-staging", "expires-at": "soon"},
    }
