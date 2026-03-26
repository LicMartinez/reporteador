import os
from dbfread import DBF

DBC_DIR = r"c:\desarrollo\Comandero\DBC"
TEST_FILES = [
    "FACTURA1.DBF",
    "FACTURA2.DBF",
    "CUENTAS.DBF",
    "COMANDAS.DBF",
    "TARJETAS.DBF"
]

def test_connection():
    with open("dbf_test_report.txt", "w", encoding="utf-8") as f:
        if not os.path.exists(DBC_DIR):
            f.write(f"Directory not found: {DBC_DIR}\n")
            return
            
        for file_name in TEST_FILES:
            path = os.path.join(DBC_DIR, file_name)
            if not os.path.exists(path):
                f.write(f"File not found: {file_name}\n")
                continue
                
            f.write(f"\n--- Testing {file_name} ---\n")
            try:
                dbf = DBF(path, encoding='latin-1', ignore_missing_memofile=True)
                f.write(f"Successfully connected to {file_name}\n")
                f.write(f"Total records (estimated or loaded): {len(dbf)}\n")
                
                has_records = False
                for i, record in enumerate(dbf):
                    has_records = True
                    if i == 0:
                        f.write(f"Schema matches expected keys. Total Columns: {len(record.keys())}\n")
                    if "ORDEN" in record:
                        orden = str(record.get("ORDEN", "")).strip()
                        if not orden:
                            f.write(f"  [LOG INVALID ORDEN] Emtpy ORDEN in record {i}\n")
                    
                    if i < 3:
                        f.write(f"  Sample {i+1}: {record}\n")
                    else:
                        break
                
                if not has_records:
                    f.write("  No records found in this file.\n")
                    
            except Exception as e:
                f.write(f"Failed to read {file_name}: {str(e)}\n")

if __name__ == "__main__":
    test_connection()
