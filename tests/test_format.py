import mapchete
from mapchete.errors import MapcheteConfigError
from mapchete.formats import available_output_formats
import numpy as np
import pytest
import xarray as xr

from mapchete.testing import get_process_mp


def test_format_available():
    assert "xarray" in available_output_formats()


def test_write_read_output(example_config):
    with mapchete.open(example_config.dict) as mp:
        data_tile = next(mp.get_process_tiles(5))

        # basic functions
        empty_xarr = mp.config.output.empty(data_tile)
        assert isinstance(empty_xarr, xr.DataArray)
        assert mp.config.output.get_path(data_tile)

        # check if tile exists
        assert not mp.config.output.tiles_exist(data_tile)

        # write
        mp.batch_process(tile=data_tile.id)

        # check if tile exists
        assert mp.config.output.tiles_exist(data_tile)

        # check if output_tile exists
        assert mp.config.output.tiles_exist(output_tile=data_tile)

        # read again, this time with data
        xarr = mp.config.output.read(data_tile)
        assert isinstance(xarr, xr.DataArray)
        assert xarr.data.all()
        assert not set(('time', 'bands', 'x', 'y')).difference(set(xarr.dims))

        # handle empty data
        process_tile = next(mp.get_process_tiles(6))
        mp.config.output.write(process_tile, mp.config.output.empty(process_tile))
        # check if tile exists
        assert not mp.config.output.tiles_exist(process_tile)
        xarr = mp.config.output.read(process_tile)
        assert isinstance(xarr, xr.DataArray)
        assert not xarr.data.any()

        # write nodata array
        process_tile = next(mp.get_process_tiles(7))
        mp.config.output.write(process_tile, xr.DataArray(np.zeros(process_tile.shape)))
        # check if tile exists
        assert not mp.config.output.tiles_exist(process_tile)
        xarr = mp.config.output.read(process_tile)
        assert isinstance(xarr, xr.DataArray)
        assert not xarr.data.any()


def test_read_from_tile_directory(xarray_tiledir_input_mapchete, written_output):
    # read from xarray tile directory output
    with mapchete.open(
        dict(
            xarray_tiledir_input_mapchete.dict,
            input=dict(xarray_output=written_output.dict["output"]["path"])
        )
    ) as mp:
        data_tile = mp.config.process_pyramid.tile(5, 0, 0)
        tile = mp.config.process_pyramid.tile(5, 0, 0)
        user_process = mapchete.MapcheteProcess(
            tile=tile,
            params=mp.config.params_at_zoom(tile.zoom),
            input=mp.config.get_inputs_for_tile(tile),
        )
        xarr_tile = user_process.open("xarray_output")
        assert not xarr_tile.is_empty()
        xarr = xarr_tile.read()
        assert isinstance(xarr, xr.DataArray)
        assert xarr.data.all()
        assert ('time', 'bands', 'x', 'y') == xarr.dims
        assert xarr.data.shape[-2:] == data_tile.shape

    # raise error if process metatiling is bigger than output metatiling
    with mapchete.open(
        dict(
            xarray_tiledir_input_mapchete.dict,
            input=dict(xarray_output=written_output.dict["output"]["path"]),
            pyramid=dict(xarray_tiledir_input_mapchete.dict["pyramid"], metatiling=4)
        )
    ) as mp:
        with pytest.raises(MapcheteConfigError):
            tile = mp.config.process_pyramid.tile(5, 0, 0)
            user_process = mapchete.MapcheteProcess(
                tile=tile,
                params=mp.config.params_at_zoom(tile.zoom),
                input=mp.config.get_inputs_for_tile(tile),
            ).open("xarray_output").read()


def test_tile_directory_grid_error(xarray_tiledir_input_mapchete, written_output):
    # raise error if tile pyramid grid differs
    with mapchete.open(
        dict(
            xarray_tiledir_input_mapchete.dict,
            input=dict(xarray_output=written_output.dict["output"]["path"]),
            pyramid=dict(grid="mercator")
        )
    ) as mp:
        with pytest.raises(MapcheteConfigError):
            tile = mp.config.process_pyramid.tile(5, 0, 0)
            mapchete.MapcheteProcess(
                tile=tile,
                params=mp.config.params_at_zoom(tile.zoom),
                input=mp.config.get_inputs_for_tile(tile),
            ).open("xarray_output").read()


def test_read_from_mapchete_output(xarray_mapchete_input_mapchete, written_output):
    # read from xarray tile directory output
    with mapchete.open(
        dict(
            xarray_mapchete_input_mapchete.dict,
            input=dict(xarray_output=written_output.dict["output"]["path"])
        )
    ) as mp:
        tile = mp.config.process_pyramid.tile(5, 0, 0)
        user_process = mapchete.MapcheteProcess(
            tile=tile,
            params=mp.config.params_at_zoom(tile.zoom),
            input=mp.config.get_inputs_for_tile(tile),
        )
        xarr_tile = user_process.open("xarray_output")
        assert not xarr_tile.is_empty()
        xarr = xarr_tile.read()
        assert isinstance(xarr, xr.DataArray)
        assert xarr.data.all()
        assert ('time', 'bands', 'x', 'y') == xarr.dims
        assert xarr.data.shape[-2:] == tile.shape

    # raise error if process metatiling is bigger than output metatiling
    with mapchete.open(
        dict(
            xarray_mapchete_input_mapchete.dict,
            input=dict(xarray_output=written_output.dict["output"]["path"]),
            pyramid=dict(xarray_mapchete_input_mapchete.dict["pyramid"], metatiling=4)
        )
    ) as mp:
        with pytest.raises(MapcheteConfigError):
            tile = mp.config.process_pyramid.tile(5, 0, 0)
            user_process = mapchete.MapcheteProcess(
                tile=tile,
                params=mp.config.params_at_zoom(tile.zoom),
                input=mp.config.get_inputs_for_tile(tile),
            ).open("xarray_output").read()


def test_write_read_remote_netcdf_output(example_config, mp_s3_tmpdir):
    with mapchete.open(
        dict(
            example_config.dict,
            output=dict(
                example_config.dict["output"],
                path=mp_s3_tmpdir
            )
        )
    ) as mp:
        data_tile = next(mp.get_process_tiles(5))

        # basic functions
        empty_xarr = mp.config.output.empty(data_tile)
        assert isinstance(empty_xarr, xr.DataArray)
        assert mp.config.output.get_path(data_tile).endswith(".nc")

        # check if tile exists
        assert not mp.config.output.tiles_exist(data_tile)

        # write
        mp.batch_process(tile=data_tile.id)

        # check if tile exists
        assert mp.config.output.tiles_exist(data_tile)

        # read again, this time with data
        xarr = mp.config.output.read(data_tile)
        assert isinstance(xarr, xr.DataArray)
        assert xarr.data.all()
        assert not set(('time', 'bands', 'x', 'y')).difference(set(xarr.dims))

        # handle empty data
        process_tile = next(mp.get_process_tiles(6))
        mp.config.output.write(process_tile, mp.config.output.empty(process_tile))
        # check if tile exists
        assert not mp.config.output.tiles_exist(process_tile)
        xarr = mp.config.output.read(process_tile)
        assert isinstance(xarr, xr.DataArray)
        assert not xarr.data.any()

        # write nodata array
        process_tile = next(mp.get_process_tiles(7))
        mp.config.output.write(process_tile, xr.DataArray(np.zeros(process_tile.shape)))
        # check if tile exists
        assert not mp.config.output.tiles_exist(process_tile)
        xarr = mp.config.output.read(process_tile)
        assert isinstance(xarr, xr.DataArray)
        assert not xarr.data.any()


def test_write_read_zarr_output(zarr_config):
    with mapchete.open(zarr_config.dict) as mp:
        data_tile = next(mp.get_process_tiles(5))

        # basic functions
        empty_xarr = mp.config.output.empty(data_tile)
        assert isinstance(empty_xarr, xr.DataArray)
        assert mp.config.output.get_path(data_tile).endswith(".zarr")

        # check if process_tile exists
        assert not mp.config.output.tiles_exist(data_tile)

        # check if output_tile exists
        assert not mp.config.output.tiles_exist(output_tile=data_tile)

        # write
        mp.batch_process(tile=data_tile.id)

        # check if tile exists
        assert mp.config.output.tiles_exist(data_tile)

        # read again, this time with data
        xarr = mp.config.output.read(data_tile)
        assert isinstance(xarr, xr.DataArray)
        assert xarr.data.all()
        assert not set(('time', 'bands', 'x', 'y')).difference(set(xarr.dims))

        # handle empty data
        process_tile = next(mp.get_process_tiles(6))
        mp.config.output.write(process_tile, mp.config.output.empty(process_tile))
        # check if tile exists
        assert not mp.config.output.tiles_exist(process_tile)
        xarr = mp.config.output.read(process_tile)
        assert isinstance(xarr, xr.DataArray)
        assert not xarr.data.any()

        # write nodata array
        process_tile = next(mp.get_process_tiles(7))
        mp.config.output.write(process_tile, xr.DataArray(np.zeros(process_tile.shape)))
        # check if tile exists
        assert not mp.config.output.tiles_exist(process_tile)
        xarr = mp.config.output.read(process_tile)
        assert isinstance(xarr, xr.DataArray)
        assert not xarr.data.any()


def test_write_read_remote_zarr_output(zarr_config, mp_s3_tmpdir):
    with mapchete.open(
        dict(
            zarr_config.dict,
            output=dict(
                zarr_config.dict["output"],
                path=mp_s3_tmpdir
            )
        )
    ) as mp:
        data_tile = next(mp.get_process_tiles(5))

        # basic functions
        empty_xarr = mp.config.output.empty(data_tile)
        assert isinstance(empty_xarr, xr.DataArray)
        assert mp.config.output.get_path(data_tile).endswith(".zarr")

        # check if tile exists
        assert not mp.config.output.tiles_exist(data_tile)

        # write
        mp.batch_process(tile=data_tile.id)

        # check if tile exists
        assert mp.config.output.tiles_exist(data_tile)

        # read again, this time with data
        xarr = mp.config.output.read(data_tile)
        assert isinstance(xarr, xr.DataArray)
        assert xarr.data.all()
        assert not set(('time', 'bands', 'x', 'y')).difference(set(xarr.dims))

        # handle empty data
        process_tile = next(mp.get_process_tiles(6))
        mp.config.output.write(process_tile, mp.config.output.empty(process_tile))
        # check if tile exists
        assert not mp.config.output.tiles_exist(process_tile)
        xarr = mp.config.output.read(process_tile)
        assert isinstance(xarr, xr.DataArray)
        assert not xarr.data.any()

        # write nodata array
        process_tile = next(mp.get_process_tiles(7))
        mp.config.output.write(process_tile, xr.DataArray(np.zeros(process_tile.shape)))
        # check if tile exists
        assert not mp.config.output.tiles_exist(process_tile)
        xarr = mp.config.output.read(process_tile)
        assert isinstance(xarr, xr.DataArray)
        assert not xarr.data.any()


def test_errors(zarr_config):
    with mapchete.open(zarr_config.dict) as mp:
        data_tile = next(mp.get_process_tiles(5))

        with pytest.raises(ValueError):
            mp.config.output.tiles_exist(
                process_tile=data_tile, output_tile=data_tile
            )

    with pytest.raises(ValueError):
        mapchete.open(
            dict(
                zarr_config.dict,
                output=dict(
                    zarr_config.dict["output"],
                    storage="invalid"
                )
            )
        )


def test_input_data(written_output):
    mp = get_process_mp(
        input=dict(xarray=written_output.dict["output"]["path"]),
        tile=written_output.first_process_tile(),
        metatiling=2
    )
    xarr = mp.open("xarray")
    assert xarr.is_empty()
    assert isinstance(xarr.read(), xr.DataArray)
