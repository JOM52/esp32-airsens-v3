"SELECT time_stamp, sensor_id.sensor_id, sensor_location.sensor_location, sensor_type.sensor_type, quantity.quantity, value"
"FROM airsens"
"INNER JOIN quantity ON airsens.quantity = quantity.id"
"INNER JOIN sensor_type ON airsens.sensor_type = sensor_type.id"
"INNER JOIN sensor_location ON airsens.sensor_location = sensor_location.id"
"INNER JOIN sensor_id ON airsens.sensor_id = sensor_id.id"
"WHERE sensor_location.sensor_location = 'mtl_2' AND quantity.quantity = 'bat'"
"ORDER BY airsens.id DESC"
"LIMIT 20;"

