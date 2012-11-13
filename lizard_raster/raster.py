"""
Reusable parts from lizard-damage
"""
from osgeo import osr
from osgeo import ogr
from osgeo import gdal
from osgeo import gdalconst

from django.conf import settings
from django.contrib.gis.geos import Polygon
from django.db import connections
#from lizard_raster import models


def reproject(ds_source, ds_match):
    """
    Reproject source to match the raster layout of match.

    Accepts and resturns gdal datasets.
    """
    nodatavalue_source = ds_source.GetRasterBand(1).GetNoDataValue()

    # Create destination dataset
    ds_destination = init_dataset(ds_match, nodatavalue=nodatavalue_source)

    # Do nearest neigbour interpolation to retain the nodata value
    projection_source = ds_source.GetProjection()
    projection_match = ds_match.GetProjection()

    gdal.ReprojectImage(
        ds_source, ds_destination,
        projection_source, projection_match,
        gdalconst.GRA_NearestNeighbour,
    )

    return ds_destination


def get_polygon(ds):
    """
    Make a polygon for the bounds of a gdal dataset
    """
    gs = ds.GetGeoTransform()
    x1 = gs[0]
    x2 = x1 + ds.RasterXSize * gs[1]
    y2 = gs[3]
    y1 = y2 + ds.RasterYSize * gs[5]
    coordinates = (
        (x1, y1),
        (x2, y1),
        (x2, y2),
        (x1, y2),
        (x1, y1),
    )
    return Polygon(coordinates, srid=28992)


def polygon_from_extent(extent):
    """ in RD
    """
    x0, y0, x1, y1 = extent
    coordinates = (
        (x0, y0),
        (x1, y0),
        (x1, y1),
        (x0, y1),
        (x0, y0), )
    return Polygon(coordinates, srid=28992)


def get_postgisraster_argument(tablename, tilename, dbname='raster'):
    """
    Return argument for PostGISRaster driver.

    From lizard-damage

    dbname is the Django database name from the project settings.
    """
    template = ' '.join("""
        PG:host=%(host)s
        port=%(port)s
        dbname='%(dbname)s'
        user='%(user)s'
        password='%(password)s'
        schema='public'
        table='%(table)s'
        where='filename=\\'%(filename)s\\''
        mode=1
    """.split())

    db = settings.DATABASES[dbname]

    if db['HOST'] == '':
        host = 'localhost'
    else:
        host = db['HOST']

    if db['PORT'] == '':
        port = '5432'
    else:
        port = db['HOST']

    return template % dict(
        host=host,
        port=port,
        dbname=db['NAME'],
        user=db['USER'],
        password=db['PASSWORD'],
        table=tablename,
        filename=tilename,
    )


def get_postgisraster_nodatavalue(tablename, tilename, dbname='raster'):
    """
    Return the nodatavalue.

    From lizard-damage.
    """
    cursor = connections[dbname].cursor()

    # Data retrieval operation - no commit required
    cursor.execute(
        """
        SELECT
            ST_BandNoDataValue(rast)
        FROM
            %(table)s
        WHERE
            filename='%(filename)s'
        """ % dict(table=tablename, filename=tilename),
    )
    row = cursor.fetchall()

    return row[0][0]


def get_geo(ds):
    """ Return tuple (projection, geotransform) """
    return  ds.GetProjection(), ds.GetGeoTransform()


def set_geo(ds, geo):
    """ Put geo in ds """
    ds.SetProjection(geo[0])
    ds.SetGeoTransform(geo[1])


# def to_masked_array(ds, mask=None):
#     """
#     Read masked array from dataset.

#     If mask is given, use that instead of creating mask from nodatavalue,
#     and check for nodatavalue in the remaining unmasked data
#     """
#     array = ds.ReadAsArray()
#     nodatavalue = ds.GetRasterBand(1).GetNoDataValue()

#     if mask is None:
#         result = numpy.ma.array(
#             array,
#             mask=numpy.equal(array, nodatavalue),
#         )
#         return result

#     result = numpy.ma.array(array, mask=mask)

#     return result


def get_mask(geo_object, shape, geo):
        """
        geo_object: often field the_geom

        Return boolean array True where the geom object is. Shape is the
        numpy shape of the raster.
        """
        sr = osr.SpatialReference()
        sr.ImportFromProj4(geo[0])
        sr_wgs84 = osr.SpatialReference()
        sr_wgs84.ImportFromEPSG(4326)

        # Prepare in-memory ogr layer
        ds_ogr = ogr.GetDriverByName(b'Memory').CreateDataSource('')
        #layer = ds_ogr.CreateLayer(b'', sr)
        layer = ds_ogr.CreateLayer(b'', sr_wgs84)
        layerdefinition = layer.GetLayerDefn()
        #for geo_object in geo_objects:

        feature = ogr.Feature(layerdefinition)
        feature.SetGeometry(ogr.CreateGeometryFromWkb(str(geo_object.wkb)))
        layer.CreateFeature(feature)

        # Prepare in-memory copy of ds_gdal
        ds_result = gdal.GetDriverByName(b'mem').Create(
            '', shape[1], shape[0], 1, gdalconst.GDT_Byte,
        )
        #set_geo(ds_result, (geo[0], sr.ExportToWkt()))
        ds_result.SetProjection(sr.ExportToWkt())
        ds_result.SetGeoTransform(geo[1])

        # Rasterize and return
        gdal.RasterizeLayer(ds_result,(1,),layer, burn_values=(1,))
        return ds_result.GetRasterBand(1).ReadAsArray()
