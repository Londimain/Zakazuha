# modules/search_engine.py
import sqlite3

class SearchEngine:
    def __init__(self, db_path):
        self.db_path = db_path

    def search(self, query, sources=None, limit=200):
        sql = ("SELECT article, name, price, pack, unit, gtin, source, old_price "
               "FROM products WHERE 1=1")
        params = []
        
        if query:
            sql += " AND (name_lower LIKE ? OR article_lower LIKE ?)"
            like = f"%{query.lower()}%"
            params += [like, like]
            
        if sources:
            placeholders = ",".join("?" * len(sources))
            sql += f" AND source IN ({placeholders})"
            params += sources
            
        sql += " LIMIT ?"
        params.append(limit)
        
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute(sql, params).fetchall()

    def search_articles_bulk(self, articles, sources=None):
        if not articles: return []
        placeholders = ",".join("?" * len(articles))
        sql = (f"SELECT article, name, price, pack, unit, gtin, source, old_price "
               f"FROM products WHERE article_lower IN ({placeholders})")
        params = [a.lower() for a in articles]
        
        if sources:
            src_placeholders = ",".join("?" * len(sources))
            sql += f" AND source IN ({src_placeholders})"
            params += sources
            
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute(sql, params).fetchall()