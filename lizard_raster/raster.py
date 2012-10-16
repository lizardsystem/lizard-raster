"""
Reusable parts from lizard-damage
"""
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

