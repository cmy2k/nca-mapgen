MAP
  CONFIG "PROJ_LIB" "/home/jmhicks/nca-mapgen/workspace/proj"
  NAME "NCA"
  PROJECTION
    #"init=epsg:5070"
    "init=epsg:4326"
  END
  #UNITS meters
  UNITS dd

  IMAGETYPE PNG24

  WEB
    METADATA
      ows_enable_request "*"
    END
  END

  $$LAYERS$$

  LAYER
    NAME "states"
    DATA "../boundaries/CONUS_4326.shp"
    TYPE POLYGON
    STATUS ON
    CLASS
      STYLE
        OUTLINECOLOR 0 0 0
	WIDTH 1
	ANTIALIAS TRUE
      END
    END
    PROJECTION
	"init=epsg:4326"
    END
  END
END
  