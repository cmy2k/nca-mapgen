MAP
  NAME "NCA"
  EXTENT -180 -90 180 90

  IMAGETYPE PNG24

  PROJECTION
    "init=epsg:4326"
  END

  WEB
    METADATA
      ows_enable_request "*"
    END
  END

  LAYER
    NAME "mask"
    DATA "tl_2014_us_state.shp"
    STATUS OFF
    TYPE POLYGON
    CLASS
      STYLE
        COLOR 0 0 0
      END
    END
  END

  $$LAYERS$$

  LAYER
    NAME "states"
    DATA "tl_2014_us_state.shp"
    STATUS ON
    TYPE POLYGON
    CLASS
      STYLE
        OUTLINECOLOR 0 0 0
	WIDTH 1
	ANTIALIAS TRUE
      END
    END
  END
END
  