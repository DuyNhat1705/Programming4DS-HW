#!/bin/sh

echo In the data/sales_messy.csv:

# (a)
echo -n + The number of data rows: 
tail  -n +2 data/sales_messy.csv | wc -l

# (b)
echo + The number of orders per status:
tail -n +2 data/sales_messy.csv | cut -d ',' -f 9 | sort | uniq -c

# (c)
echo -n + The total revenue of shipped order: 
awk -F ',' 'NR > 1 && $9 == "shipped" && $8 != "" {total += $8 * $7} END {print total}' data/sales_messy.csv
