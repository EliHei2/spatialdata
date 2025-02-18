from typing import Optional, Union

import numpy as np
import pandas as pd
import pytest
from anndata import AnnData
from dask.dataframe.core import DataFrame as DaskDataFrame
from geopandas import GeoDataFrame
from multiscale_spatial_image import MultiscaleSpatialImage
from numpy.random import default_rng
from shapely.geometry import MultiPolygon, Point, Polygon
from spatial_image import SpatialImage
from xarray import DataArray

from spatialdata import SpatialData
from spatialdata._core.models import (
    Image2DModel,
    Image3DModel,
    Labels2DModel,
    Labels3DModel,
    PointsModel,
    ShapesModel,
    TableModel,
)

RNG = default_rng()


@pytest.fixture()
def images() -> SpatialData:
    return SpatialData(images=_get_images())


@pytest.fixture()
def labels() -> SpatialData:
    return SpatialData(labels=_get_labels())


@pytest.fixture()
def shapes() -> SpatialData:
    return SpatialData(shapes=_get_shapes())


@pytest.fixture()
def points() -> SpatialData:
    return SpatialData(points=_get_points())


@pytest.fixture()
def table_single_annotation() -> SpatialData:
    return SpatialData(table=_get_table(region="sample1"))


@pytest.fixture()
def table_multiple_annotations() -> SpatialData:
    return SpatialData(table=_get_table(region=["sample1", "sample2"]))


@pytest.fixture()
def tables() -> list[AnnData]:
    _tables = []
    for region, region_key, instance_key in (
        [None, None, None],
        ["my_region0", None, "my_instance_key"],
        [["my_region0", "my_region1"], "my_region_key", "my_instance_key"],
    ):
        _tables.append(_get_table(region=region, region_key=region_key, instance_key=instance_key))
    return _tables


@pytest.fixture()
def full_sdata() -> SpatialData:
    return SpatialData(
        images=_get_images(),
        labels=_get_labels(),
        shapes=_get_shapes(),
        points=_get_points(),
        table=_get_table(region="sample1"),
    )


# @pytest.fixture()
# def empty_points() -> SpatialData:
#     geo_df = GeoDataFrame(
#         geometry=[],
#     )
#     from spatialdata import NgffIdentity
#     _set_transformations(geo_df, NgffIdentity())
#
#     return SpatialData(points={"empty": geo_df})


@pytest.fixture()
def empty_table() -> SpatialData:
    adata = AnnData(shape=(0, 0))
    adata = TableModel.parse(adata=adata)
    return SpatialData(table=adata)


@pytest.fixture(
    # params=["labels"]
    params=["full", "empty"]
    + ["images", "labels", "points", "table_single_annotation", "table_multiple_annotations"]
    + ["empty_" + x for x in ["table"]]
)
def sdata(request) -> SpatialData:
    if request.param == "full":
        s = SpatialData(
            images=_get_images(),
            labels=_get_labels(),
            shapes=_get_shapes(),
            points=_get_points(),
            table=_get_table("sample1"),
        )
    elif request.param == "empty":
        s = SpatialData()
    else:
        s = request.getfixturevalue(request.param)
    # print(f"request.param = {request.param}")
    return s


def _get_images() -> dict[str, Union[SpatialImage, MultiscaleSpatialImage]]:
    out = {}
    dims_2d = ("c", "y", "x")
    dims_3d = ("z", "y", "x", "c")
    out["image2d"] = Image2DModel.parse(RNG.normal(size=(3, 64, 64)), dims=dims_2d)
    out["image2d_multiscale"] = Image2DModel.parse(RNG.normal(size=(3, 64, 64)), scale_factors=[2, 2], dims=dims_2d)
    out["image2d_xarray"] = Image2DModel.parse(DataArray(RNG.normal(size=(3, 64, 64)), dims=dims_2d), dims=None)
    out["image2d_multiscale_xarray"] = Image2DModel.parse(
        DataArray(RNG.normal(size=(3, 64, 64)), dims=dims_2d),
        scale_factors=[2, 4],
        dims=None,
    )
    out["image3d_numpy"] = Image3DModel.parse(RNG.normal(size=(2, 64, 64, 3)), dims=dims_3d)
    out["image3d_multiscale_numpy"] = Image3DModel.parse(
        RNG.normal(size=(2, 64, 64, 3)), scale_factors=[2], dims=dims_3d
    )
    out["image3d_xarray"] = Image3DModel.parse(DataArray(RNG.normal(size=(2, 64, 64, 3)), dims=dims_3d), dims=None)
    out["image3d_multiscale_xarray"] = Image3DModel.parse(
        DataArray(RNG.normal(size=(2, 64, 64, 3)), dims=dims_3d),
        scale_factors=[2],
        dims=None,
    )
    return out


def _get_labels() -> dict[str, Union[SpatialImage, MultiscaleSpatialImage]]:
    out = {}
    dims_2d = ("y", "x")
    dims_3d = ("z", "y", "x")

    out["labels2d"] = Labels2DModel.parse(RNG.normal(size=(64, 64)), dims=dims_2d)
    out["labels2d_multiscale"] = Labels2DModel.parse(RNG.normal(size=(64, 64)), scale_factors=[2, 4], dims=dims_2d)
    out["labels2d_xarray"] = Labels2DModel.parse(DataArray(RNG.normal(size=(64, 64)), dims=dims_2d), dims=None)
    out["labels2d_multiscale_xarray"] = Labels2DModel.parse(
        DataArray(RNG.normal(size=(64, 64)), dims=dims_2d),
        scale_factors=[2, 4],
        dims=None,
    )
    out["labels3d_numpy"] = Labels3DModel.parse(RNG.normal(size=(10, 64, 64)), dims=dims_3d)
    out["labels3d_multiscale_numpy"] = Labels3DModel.parse(
        RNG.normal(size=(10, 64, 64)), scale_factors=[2, 4], dims=dims_3d
    )
    out["labels3d_xarray"] = Labels3DModel.parse(DataArray(RNG.normal(size=(10, 64, 64)), dims=dims_3d), dims=None)
    out["labels3d_multiscale_xarray"] = Labels3DModel.parse(
        DataArray(RNG.normal(size=(10, 64, 64)), dims=dims_3d),
        scale_factors=[2, 4],
        dims=None,
    )
    return out


def _get_shapes() -> dict[str, GeoDataFrame]:
    # TODO: add polygons from geojson and from ragged arrays since now only the GeoDataFrame initializer is tested.
    out = {}
    poly = GeoDataFrame(
        {
            "geometry": [
                Polygon(((0, 0), (0, 1), (1, 1), (1, 0))),
                Polygon(((0, 0), (0, -1), (-1, -1), (-1, 0))),
                Polygon(((0, 0), (0, 1), (1, 10))),
                Polygon(((0, 0), (0, 1), (1, 1))),
                Polygon(((0, 0), (0, 1), (1, 1), (1, 0), (1, 0))),
            ]
        }
    )

    multipoly = GeoDataFrame(
        {
            "geometry": [
                MultiPolygon(
                    [
                        Polygon(((0, 0), (0, 1), (1, 1), (1, 0))),
                        Polygon(((0, 0), (0, -1), (-1, -1), (-1, 0))),
                    ]
                ),
                MultiPolygon(
                    [
                        Polygon(((0, 0), (0, 1), (1, 10))),
                        Polygon(((0, 0), (0, 1), (1, 1))),
                        Polygon(((0, 0), (0, 1), (1, 1), (1, 0), (1, 0))),
                    ]
                ),
            ]
        }
    )

    points = GeoDataFrame(
        {
            "geometry": [
                Point((0, 1)),
                Point((1, 1)),
                Point((3, 4)),
                Point((4, 2)),
                Point((5, 6)),
            ]
        }
    )
    points["radius"] = np.random.normal(size=(len(points), 1))

    out["poly"] = ShapesModel.parse(poly)
    out["multipoly"] = ShapesModel.parse(multipoly)
    out["circles"] = ShapesModel.parse(points)

    return out


def _get_points() -> dict[str, DaskDataFrame]:
    name = "points"
    out = {}
    for i in range(2):
        name = f"{name}_{i}"
        arr = RNG.normal(size=(100, 2))
        # randomly assign some values from v to the points
        points_assignment0 = RNG.integers(0, 10, size=arr.shape[0]).astype(np.int_)
        genes = RNG.choice(["a", "b"], size=arr.shape[0])
        annotation = pd.DataFrame(
            {
                "genes": genes,
                "instance_id": points_assignment0,
            },
        )
        out[name] = PointsModel.parse(arr, annotation=annotation, feature_key="genes", instance_key="instance_id")
    return out


def _get_table(
    region: Optional[Union[str, list[str]]],
    region_key: Optional[str] = None,
    instance_key: Optional[str] = None,
) -> AnnData:
    if region is not None:
        region_key = region_key or "annotated_region"
        instance_key = instance_key or "instance_id"
    adata = AnnData(RNG.normal(size=(100, 10)), obs=pd.DataFrame(RNG.normal(size=(100, 3)), columns=["a", "b", "c"]))
    if instance_key is not None:
        adata.obs[instance_key] = np.arange(adata.n_obs)
    if isinstance(region, str):
        return TableModel.parse(adata=adata, region=region, instance_key=instance_key)
    elif isinstance(region, list):
        adata.obs[region_key] = RNG.choice(region, size=adata.n_obs)
        adata.obs[instance_key] = RNG.integers(0, 10, size=(100,))
        return TableModel.parse(adata=adata, region=region, region_key=region_key, instance_key=instance_key)
    elif region is None:
        return TableModel.parse(adata=adata)
    else:
        raise ValueError(f"region must be a string or list of strings, not {type(region)}")
