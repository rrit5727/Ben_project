import fitz
from collections import defaultdict
import pandas as pd
import glob
import os
from datetime import datetime

def get_sorted_text(arg_box_infos):
    lines_group = defaultdict(list)
    for x in arg_box_infos:
        lines_group[x[1]//3].append(x)
    block_info = []
    for line_num in sorted(lines_group.keys()):
        block_info.append([y[4] for y in sorted(lines_group[line_num], key = lambda x : x[0])])
    return block_info

def get_splits(arg_file):
    doc = fitz.open(arg_file)
    splits = [[]]
    for page in doc:
        lines = defaultdict(list)
        for each_word in page.get_text("words"):
            lines[each_word[3]//6].append(each_word)
        for key in sorted(lines.keys()):
            line_info = list(map(lambda x : x[4], sorted(lines[key], key = lambda x : x[0])))
            if len(set('European|Article|Number|(EAN)|Quantity|UoM'.split('|')) & set(line_info)) == 6:
                splits.append([])
            splits[-1].extend(lines[key])
    splits = splits[1:]
    return splits

def get_ean_info(arg_split):
    lines = defaultdict(list)
    key_info = {}
    for each_word in arg_split:
        lines[each_word[3]//2].append(each_word)
    for key in sorted(lines.keys()):
        line_info = list(map(lambda x : x[4], sorted(lines[key], key = lambda x : x[0])))
        if len(line_info) > 3 and line_info[1].isdigit() and len(line_info[1]) == 13 and 'Each' in line_info:
            line_info = [each_cell for each_cell in line_info if each_cell != 'Quantity:']
            key_info = {
                "Purchase Order" : None,
                "EAN" : "'" + line_info[1],
                # "Quantity" : line_info[2],
                "UoM" : line_info[3],
                "Unit Price" : line_info[4],
                # "Total" : line_info[5]
            }
    return key_info

def process_arg_row(arg_split):
    ean_info = get_ean_info(arg_split)
    # df = pd.DataFrame(arg_split)
    loc_nums_info = [each_word for each_word in arg_split if each_word[4] == "Number:"]
    main_infos = defaultdict(list)
    ind = 0
    for each_loc in loc_nums_info:
        infos = [each_loc]
        for each_cell in arg_split:
            if each_loc[0]-40 < each_cell[0] < each_loc[0]-30 and each_loc[1]-3 < each_cell[1] < each_loc[1] + 3 and each_loc[2]-40 < each_cell[2] < each_loc[2]-30 and each_loc[3]-3 < each_cell[3] < each_loc[3]+3:
                infos.append(each_cell)
            if each_loc[0]+40 < each_cell[0] < each_loc[0]+50 and each_loc[1]-5 < each_cell[1] < each_loc[1] and each_loc[2]+25 < each_cell[2] < each_loc[2]+35 and each_loc[3]-5 < each_cell[3] < each_loc[3]:
                infos.append(each_cell)
        if sorted([each[4] for each in infos])[0].isdigit() and len(set(['Location', 'Number:']) & set([each[4] for each in infos])) == 2:
            ind += 1
            main_infos[ind].extend(infos)
    ind = 0
    quants_info = [each_word for each_word in arg_split if each_word[4] == "Quantity:"]
    for each_quant in quants_info:
        infos = []
        for each_cell in arg_split:
            if each_quant[0]+75 < each_cell[0] < each_quant[0]+85 and each_quant[1]-4 < each_cell[1] < each_quant[1]+4 and each_quant[2]+45 < each_cell[2] < each_quant[2]+60 and each_quant[3]-4 < each_cell[3] < each_quant[3]+4:
                infos.append(each_cell)
        if sorted([each[4] for each in infos])[0].isdigit():
            ind += 1
            main_infos[ind].extend([each_quant, infos[-1]])
    rows = []
    for each_val in main_infos.values():
        key, val = [each_cell for each_cell in map(lambda x : x[4], each_val) if each_cell.isdigit()]
        row_data = ean_info.copy()
        row_data["Store"], row_data["Qty"] = key, val
        rows.append(row_data)
    return rows

def get_quantities_by_store_df(arg_file):
    splits = get_splits(arg_file)
    rows = []
    for each_split in splits:
        rows.extend(process_arg_row(each_split))
    df = pd.DataFrame(rows)
    with fitz.open(arg_file) as doc:
        for each_line in get_sorted_text(doc[0].get_text('words')):
            if len(set(['Reference', '#:']) & set(each_line)) == 2:
                df['Purchase Order'] = each_line[-1]
                break
    return df.to_dict('records')
    
def get_packing_by_store_df(arg_file):
    doc = fitz.open(arg_file)
    lines = []
    for page in doc:
        lines.extend(get_sorted_text(page.get_text("words")))
    doc.close()
    n, row_data, orders = len(lines), {}, []
    for ind, each_line in enumerate(lines):
        if len(set(['Order', 'Level']) & set(each_line)) == 2 and ind + 3 < n and len(set(['Purchase', 'Order', 'Reference', 'Information', 'Buying', 'Party', 'Customer']) & set(sum([lines[x] for x in range(ind-3, ind + 7)], []))) == 7:
            orders.append(row_data)
            row_data = {"Items" : []}
        if len(set(['Customer', 'Order']) & set(each_line)) == 2 and ind + 1 < n:
            row_data['Purchase Order'] = [each_word for each_word in sum([lines[x] for x in range(ind-1, ind+2)], []) if each_word.isdigit()][0]
        if len(set(['Assigned', 'by', 'Buyer:']) & set(each_line)) == 3 and each_line[-1].isdigit():
            row_data['Buyer Number'] = each_line[-1]
        if len(set(['Company', 'Name:']) & set(each_line)) == 2 and ind + 3 < n and len(set(['Purchase', 'Order', 'Reference', 'Information', 'Buying', 'Party', 'Customer', 'Assigned', 'by', 'Buyer:']) & set(sum([lines[x] for x in range(ind-3, ind + 7)], []))) == 10:
            row_data['Buyer Company Name'] = (" ".join(each_line)).split('Company Name:')[-1].strip()
        if len(set(['Pack', 'Level']) & set(each_line)) == 2 and ind + 3 < n and len(set(['SSCC-18', 'European', 'Article', 'Number', '(EAN)']) & set(sum([lines[x] for x in range(ind-3, ind + 6)], []))) == 5:
            row_data['SSCC-18'] = [each_word for each_word in sum([lines[x] for x in range(ind-3, ind + 6)], []) if each_word.isdigit() and len(each_word) == 20][0]
        if len(set(['European', 'Article', 'Number', '(EAN)']) & set(each_line)) == 4:
            row_data['Items'].append({})
            row_data['Items'][-1].update({'EAN' : each_line[-1]})
            for x in range(ind, ind + 5):
                if len(set(['Quantity', 'Shipped:']) & set(lines[x])) == 2:
                    row_data['Items'][-1].update({
                        'QTY' : (" ".join(lines[x])).split('Quantity Shipped:')[-1].split()[0]
                    })
    orders.append(row_data)
    df = pd.DataFrame(orders[1:])
    df = df.explode('Items', ignore_index = True)
    df[['EAN', 'QTY']] = pd.json_normalize(df['Items'])
    df['EAN'] = "'" + df['EAN']
    df['SSCC-18'] = "'" + df['SSCC-18']
    df = df[['Purchase Order', 'Buyer Company Name', 'Buyer Number',
           'SSCC-18', 'EAN', 'QTY']]
    return df.to_dict('records')

def process_files():
    os.makedirs('Output', exist_ok = True)
    store_info = {"quantity-by-store" : [], "packing-by-store" : []}
    for each_file in glob.glob("Input/*.pdf"):
        with fitz.open(each_file) as doc:
            text = doc[0].get_text()
        if not "Ship Notice Information" in text:
            store_info["quantity-by-store"].extend(get_quantities_by_store_df(each_file))
        else:
            store_info["packing-by-store"].extend(get_packing_by_store_df(each_file))
    store_info = {key : pd.DataFrame(val) for key, val in store_info.items()}
    run_time = datetime.now().strftime("%d.%m.%y.%H.%M.%S")
    for key, df in store_info.items():
        df.to_csv(f"Output/{key}-{run_time}.csv", index = False)

process_files()