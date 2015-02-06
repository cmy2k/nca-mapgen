import csv

fields = ['Zonal_Dir','LON','Merdian_Dir','LAT,P2021_2050','Stat_sig_50','P2041_2070','Stat_sig_70','P2070_2099','Stat_sig_99']

with open('foo', 'wt') as file_out:
    with open('A2-t2m-ave.csv', 'rb') as file_in:
        reader = csv.DictReader(file_in, fieldnames=fields)
        writer = csv.DictWriter(file_out, fieldnames=fields)
        writer.writeheader()
        reader.next()
        for row in reader:
            row['LON'] = str(float(row['LON']) - 180)
            writer.writerow(row)
