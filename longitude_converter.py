import csv

fields = ['Zonal_Dir','LON','Merdian_Dir','LAT','P2021_2050','Stat_sig_50','P2041_2070','Stat_sig_70','P2070_2099','Stat_sig_99']
input_name = 'A2-t2m-ave.csv'
output_name = 'A2-t2m-ave_180.csv'

with open(output_name, 'wt') as file_out:
    with open(input_name, 'rb') as file_in:
        reader = csv.DictReader(file_in, fieldnames=fields)
        writer = csv.DictWriter(file_out, fieldnames=fields)
        writer.writeheader()
        reader.next()
        for row in reader:
            lon = float(row['LON'])
            if lon >= 180:
                row['LON'] = lon - 360
            writer.writerow(row)
