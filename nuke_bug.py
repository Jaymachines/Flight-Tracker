import sqlite3

def nuke_under_600():
    conn = sqlite3.connect("flight_data.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM prices WHERE price < 600")
    count_before = cursor.fetchone()[0]
    
    if count_before > 0:
        sql = "DELETE FROM prices WHERE price < 600"
        cursor.execute(sql)
        conn.commit()
        print(f"Nettoyage terminé : {count_before} prix fantômes (sous 600$) ont été supprimés.")
    else:
        print("Le coffre-fort est propre. Aucun prix sous 600$ n'a été trouvé.")
        
    conn.close()

if __name__ == "__main__":
    print("ATTENTION : Nettoyage radical.")
    print("Cela va supprimer TOUS les vols coûtant moins de 600$.")
    input("Appuie sur Entrée pour déclencher ou Ctrl+C pour annuler...")
    nuke_under_600()