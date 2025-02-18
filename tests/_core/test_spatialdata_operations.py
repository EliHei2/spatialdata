import numpy as np
import pytest
from anndata import AnnData
from dask.dataframe.core import DataFrame as DaskDataFrame
from dask.delayed import Delayed
from geopandas import GeoDataFrame
from multiscale_spatial_image import MultiscaleSpatialImage
from spatial_image import SpatialImage

from spatialdata import SpatialData
from spatialdata._core._spatialdata_ops import (
    _concatenate_tables,
    concatenate,
    set_transformation,
)
from spatialdata._core.models import TableModel
from spatialdata._core.transformations import Identity, Scale
from tests.conftest import _get_table


def _assert_elements_left_to_right_seem_identical(sdata0: SpatialData, sdata1: SpatialData):
    for element_type, element_name, element in sdata0._gen_elements():
        elements = sdata1.__getattribute__(element_type)
        assert element_name in elements
        element1 = elements[element_name]
        if isinstance(element, AnnData) or isinstance(element, SpatialImage) or isinstance(element, GeoDataFrame):
            assert element.shape == element1.shape
        elif isinstance(element, DaskDataFrame):
            for s0, s1 in zip(element.shape, element1.shape):
                if isinstance(s0, Delayed):
                    s0 = s0.compute()
                if isinstance(s1, Delayed):
                    s1 = s1.compute()
                assert s0 == s1
        elif isinstance(element, MultiscaleSpatialImage):
            assert len(element) == len(element1)
        else:
            raise TypeError(f"Unsupported type {type(element)}")


def _assert_tables_seem_identical(table0: AnnData, table1: AnnData):
    assert table0.shape == table1.shape


def _assert_spatialdata_objects_seem_identical(sdata0: SpatialData, sdata1: SpatialData):
    # this is not a full comparison, but it's fine anyway
    assert len(list(sdata0._gen_elements())) == len(list(sdata1._gen_elements()))
    assert set(sdata0.coordinate_systems) == set(sdata1.coordinate_systems)
    _assert_elements_left_to_right_seem_identical(sdata0, sdata1)
    _assert_elements_left_to_right_seem_identical(sdata1, sdata0)
    _assert_tables_seem_identical(sdata0.table, sdata1.table)


def test_filter_by_coordinate_system(full_sdata):
    sdata = full_sdata.filter_by_coordinate_system(coordinate_system="global", filter_table=False)
    _assert_spatialdata_objects_seem_identical(sdata, full_sdata)

    scale = Scale([2.0], axes=("x",))
    set_transformation(full_sdata.images["image2d"], scale, "my_space0")
    set_transformation(full_sdata.shapes["circles"], Identity(), "my_space0")
    set_transformation(full_sdata.shapes["poly"], Identity(), "my_space1")

    sdata_my_space = full_sdata.filter_by_coordinate_system(coordinate_system="my_space0", filter_table=False)
    assert len(list(sdata_my_space._gen_elements())) == 2
    _assert_tables_seem_identical(sdata_my_space.table, full_sdata.table)

    sdata_my_space1 = full_sdata.filter_by_coordinate_system(
        coordinate_system=["my_space0", "my_space1", "my_space2"], filter_table=False
    )
    assert len(list(sdata_my_space1._gen_elements())) == 3


def test_filter_by_coordinate_system_also_table(full_sdata):
    from spatialdata._core.models import TableModel

    full_sdata.table.obs["annotated_shapes"] = np.random.choice(
        ["shapes/circles", "shapes/poly"], size=full_sdata.table.shape[0]
    )
    adata = full_sdata.table
    del adata.uns[TableModel.ATTRS_KEY]
    del full_sdata.table
    full_sdata.table = TableModel.parse(
        adata, region=["shapes/circles", "shapes/poly"], region_key="annotated_shapes", instance_key="instance_id"
    )

    scale = Scale([2.0], axes=("x",))
    set_transformation(full_sdata.shapes["circles"], scale, "my_space0")
    set_transformation(full_sdata.shapes["poly"], scale, "my_space1")

    filtered_sdata0 = full_sdata.filter_by_coordinate_system(coordinate_system="my_space0")
    filtered_sdata1 = full_sdata.filter_by_coordinate_system(coordinate_system="my_space1")
    filtered_sdata2 = full_sdata.filter_by_coordinate_system(coordinate_system="my_space0", filter_table=False)

    assert len(filtered_sdata0.table) + len(filtered_sdata1.table) == len(full_sdata.table)
    assert len(filtered_sdata2.table) == len(full_sdata.table)


def test_concatenate_tables():
    """
    The concatenation uses AnnData.concatenate(), here we test the contatenation result on region, region_key, instance_key
    """
    table0 = _get_table(region="shapes/circles", region_key=None, instance_key="instance_id")
    table1 = _get_table(region="shapes/poly", region_key=None, instance_key="instance_id")
    table2 = _get_table(region="shapes/poly", region_key=None, instance_key="instance_id")
    assert _concatenate_tables([]) is None
    assert len(_concatenate_tables([table0])) == len(table0)
    assert len(_concatenate_tables([table0, table1, table2])) == len(table0) + len(table1) + len(table2)

    ##
    table0.obs["annotated_element_merged"] = np.arange(len(table0))
    c0 = _concatenate_tables([table0, table1])
    assert len(c0) == len(table0) + len(table1)

    d = c0.uns[TableModel.ATTRS_KEY]
    d["region"] = sorted(d["region"])
    assert d == {
        "region": ["shapes/circles", "shapes/poly"],
        "region_key": "annotated_element_merged_1",
        "instance_key": "instance_id",
    }

    ##
    table3 = _get_table(region="shapes/circles", region_key="annotated_shapes_other", instance_key="instance_id")
    table3.uns[TableModel.ATTRS_KEY]["region_key"] = "annotated_shapes_other"
    with pytest.raises(AssertionError):
        _concatenate_tables([table0, table3])
    table3.uns[TableModel.ATTRS_KEY]["region_key"] = None
    table3.uns[TableModel.ATTRS_KEY]["instance_key"] = ["shapes/circles", "shapes/poly"]
    with pytest.raises(AssertionError):
        _concatenate_tables([table0, table3])

    ##
    table4 = _get_table(
        region=["shapes/circles", "shapes/poly"], region_key="annotated_shape0", instance_key="instance_id"
    )
    table5 = _get_table(
        region=["shapes/circles", "shapes/poly"], region_key="annotated_shape0", instance_key="instance_id"
    )
    table6 = _get_table(
        region=["shapes/circles", "shapes/poly"], region_key="annotated_shape1", instance_key="instance_id"
    )

    assert len(_concatenate_tables([table4, table5])) == len(table4) + len(table5)

    with pytest.raises(RuntimeError):
        _concatenate_tables([table4, table6])


def test_concatenate_sdatas(full_sdata):
    with pytest.raises(RuntimeError):
        concatenate([full_sdata, SpatialData(images={"image2d": full_sdata.images["image2d"]})])
    with pytest.raises(RuntimeError):
        concatenate([full_sdata, SpatialData(labels={"labels2d": full_sdata.labels["labels2d"]})])
    with pytest.raises(RuntimeError):
        concatenate([full_sdata, SpatialData(points={"points_0": full_sdata.points["points_0"]})])
    with pytest.raises(RuntimeError):
        concatenate([full_sdata, SpatialData(shapes={"circles": full_sdata.shapes["circles"]})])

    assert concatenate([full_sdata, SpatialData()]).table is not None
    assert concatenate([full_sdata, SpatialData()], omit_table=True).table is None

    set_transformation(full_sdata.shapes["circles"], Identity(), "my_space0")
    set_transformation(full_sdata.shapes["poly"], Identity(), "my_space1")
    filtered = full_sdata.filter_by_coordinate_system(coordinate_system=["my_space0", "my_space1"], filter_table=False)
    assert len(list(filtered._gen_elements())) == 2
    filtered0 = filtered.filter_by_coordinate_system(coordinate_system="my_space0", filter_table=False)
    filtered1 = filtered.filter_by_coordinate_system(coordinate_system="my_space1", filter_table=False)
    concatenated = concatenate([filtered0, filtered1])
    assert len(list(concatenated._gen_elements())) == 2


def test_locate_spatial_element(full_sdata):
    assert full_sdata._locate_spatial_element(full_sdata.images["image2d"]) == ("image2d", "images")
    im = full_sdata.images["image2d"]
    del full_sdata.images["image2d"]
    with pytest.raises(ValueError, match="Element not found in the SpatialData object."):
        full_sdata._locate_spatial_element(im)
    full_sdata.images["image2d"] = im
    full_sdata.images["image2d_again"] = im
    with pytest.raises(ValueError):
        full_sdata._locate_spatial_element(im)
