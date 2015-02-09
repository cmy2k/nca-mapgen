# nca-mapgen
Scripts to help automate generating map images from model data provided by NCA

## Thoughts
The following are some thoughts on how this might be approached.

Arguments:
- Input CSV
- List of raster columns
- List of stats columns
- Pixel resolution X,Y
- Path to directory of clip shapes
- Mapfile path (can contain references to other map elements)

Example input:
- A2-t2m-ave.csv
- boundaries/  
  - conus.shp
  - hi.shp
  - ak.shp
- config.json
```json
{
  'layers': [
    {
      'data': 'P2021_2050',
      'stat': 'Stat_sig_50'
    }, {
      'data': 'P2041_2070',
      'stat': 'Stat_sig_70'
    }, {
      'data': 'P2070_2099',
      'stat': 'Stat_sig_99'
    }    
  ],
  'template': A2-t2m-ave.map.tpl,
  'xres': 2.8125,
  'yres': 2.79
}
```

Output:
A2-t2m-ave/  

__temp/
____ A2-t2m-ave_180.csv  
____ A2-t2m-ave.vrt  
____ A2-t2m-ave__conus.shp  
____ A2-t2m-ave__hi.shp  
____ A2-t2m-ave__ak.shp  

__ data/  
____ A2-t2m-ave__P2021_2050__conus.tif  
____ A2-t2m-ave__P2021_2050__hi.tif  
____ A2-t2m-ave__P2021_2050__ak.tif  
____ A2-t2m-ave__P2041_2070__conus.tif  
____ A2-t2m-ave__P2041_2070__hi.tif  
____ A2-t2m-ave__P2041_2070__ak.tif  
____ A2-t2m-ave__P2070_2099__conus.tif  
____ A2-t2m-ave__P2070_2099__hi.tif  
____ A2-t2m-ave__P2070_2099__ak.tif  

__ renders/  
____ A2-t2m-ave__P2021_2050__conus.png  
____ A2-t2m-ave__P2021_2050__hi.png  
____ A2-t2m-ave__P2021_2050__ak.png  
____ A2-t2m-ave__P2041_2070__conus.png  
____ A2-t2m-ave__P2041_2070__hi.png  
____ A2-t2m-ave__P2041_2070__ak.png  
____ A2-t2m-ave__P2070_2099__conus.png  
____ A2-t2m-ave__P2070_2099__hi.png  
____ A2-t2m-ave__P2070_2099__ak.png  

Note:  
Generally, the process of rasterize, then clip, is that there's some odd things that happen to the outputs. They don't quite line up with the original, and this is potentially very problematic with the data representation.

### 0 (if necessary): Subtract 180 from all longitudes
The source data has longitudes ranging from 0 to 360. It is more common for WGS84 data to be presented in a range of -180 to 180. To make processing easier later, all rows are looped over, and each longitude value is subtracted by 180.

### 1: Column arg, generate VRT to wrap CSV
Assuming A2-t2m-ave.csv (or derived from step 0: A2-t2m-ave.csv) with data columns: P2021_2050, P2041_2070, P2070_2099

A2-t2m-ave.vrt
```xml
<OGRVRTDataSource>
  <OGRVRTLayer name="A2-t2m-ave">
    <SrcDataSource relativeToVRT="1">A2-t2m-ave_180.csv</SrcDataSource>
    <GeometryType>wkbPoint</GeometryType>
    <LayerSRS>WGS84</LayerSRS>
    <GeometryField encoding="PointFromColumns" x="LON" y="LAT" />
    <Field name="P2021_2050" src="P2021_2050" type="Real" />
    <Field name="P2041_2070" src="P2041_2070" type="Real" />
    <Field name="P2070_2099" src="P2070_2099" type="Real" />
  </OGRVRTLayer>
</OGRVRTDataSource>
```

### 3: Find extent of each clip boundary
Attempting to clip the vrt using ogr2ogr -clipsrc with a shapefile specified is _very_ slow. I think a better procedure will be to get general boxes for the features, then clip to those. This is incredibly faster, plus it gives some spillover around the shape which is desirable.

Do this for every clip:
```
ogrinfo -so input/boundaries/conus.shp conus | grep "Extent: "
-->> Extent: (-124.848974, 24.396308) - (-66.885444, 49.384358)
```

Then:
```
ogr2ogr -clipsrc -124.848974 24.396308 -66.885444 49.384358  A2-t2m-ave/temp/A2-t2m-ave__conus.shp A2-t2m-ave/temp/A2-t2m-ave.vrt
```

### 4: gdal_rasterize on each column of each extent shapefile
gdal_rasterize -tr 2.8125 2.79 -l A2-t2m-ave__conus -a P2021_2050 A2-t2m-ave/temp/A2-t2m-ave__conus.shp A2-t2m-ave/data/A2-t2m-ave__P2021_2050__conus.tif

This creates unstyled rasters for each extent and attribute combination.

### TODO:
- How to handle significance?
- Style rasters