#!/usr/bin/env python3
"""
Script para poblar PostgreSQL (MS1) con 20,000 clientes
"""
import psycopg2
from faker import Faker
import random
from datetime import datetime, timedelta
import sys

fake = Faker('es_ES')

# Configuración de PostgreSQL
DB_CONFIG = {
    'host': 'localhost',  # Ejecutar desde el mismo EC2 de MS1
    'port': 5432,
    'database': 'clientes_db',
    'user': 'admin',
    'password': 'admin123'
}

def create_connection():
    """Crear conexión a PostgreSQL"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print("✅ Conectado a PostgreSQL (MS1)")
        return conn
    except Exception as e:
        print(f"❌ Error conectando a PostgreSQL: {e}")
        sys.exit(1)

def clear_tables(conn):
    """Limpiar tablas existentes"""
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM documentos_identidad;")
        cursor.execute("DELETE FROM clientes;")
        conn.commit()
        print("🧹 Tablas limpiadas")
    except Exception as e:
        conn.rollback()
        print(f"⚠️  Error limpiando tablas: {e}")
    finally:
        cursor.close()

def insert_clientes_batch(conn, num_records=20000, batch_size=1000):
    """Insertar clientes en lotes"""
    cursor = conn.cursor()
    total_inserted = 0
    
    print(f"📝 Insertando {num_records} clientes en lotes de {batch_size}...")
    
    # Set para rastrear números de documento ya usados
    numeros_usados = set()
    
    for batch_start in range(0, num_records, batch_size):
        clientes_batch = []
        documentos_batch = []
        
        for i in range(batch_start, min(batch_start + batch_size, num_records)):
            cliente_id = i + 1
            
            # Datos del cliente
            nombre = fake.first_name()
            apellido = fake.last_name()
            email = f"{nombre.lower()}.{apellido.lower()}{cliente_id}@{fake.free_email_domain()}"
            telefono = fake.phone_number()[:15]
            estado = random.choice(['activo', 'activo', 'activo', 'inactivo'])  # 75% activos
            fecha_registro = datetime.now() - timedelta(days=random.randint(0, 365*5))
            
            clientes_batch.append((
                cliente_id, nombre, apellido, email, telefono, fecha_registro, estado
            ))
            
            # Documento de identidad - GARANTIZAR UNICIDAD
            tipo_doc = random.choice(['DNI', 'DNI', 'DNI', 'Pasaporte', 'Carnet Extranjeria'])  # Mayoría DNI
            
            # Generar número único
            numero_doc = None
            intentos = 0
            while numero_doc is None or numero_doc in numeros_usados:
                if tipo_doc == 'DNI':
                    # DNI de 8 dígitos único
                    numero_doc = str(10000000 + cliente_id + intentos * 100000).zfill(8)
                elif tipo_doc == 'Pasaporte':
                    # Pasaporte único
                    numero_doc = f"P{(1000000 + cliente_id + intentos * 100000):07d}"
                else:
                    # Carnet Extranjeria único
                    numero_doc = str(100000000 + cliente_id + intentos * 1000000)
                intentos += 1
                if intentos > 100:  # Evitar loop infinito
                    break
            
            numeros_usados.add(numero_doc)
            
            fecha_emision = fecha_registro.date()
            fecha_vencimiento = fecha_emision + timedelta(days=random.randint(365*3, 365*10))
            
            documentos_batch.append((
                cliente_id, tipo_doc, numero_doc, fecha_emision, fecha_vencimiento
            ))
        
        # Insertar lote de clientes
        try:
            cursor.executemany("""
                INSERT INTO clientes 
                (cliente_id, nombre, apellido, email, telefono, fecha_registro, estado)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, clientes_batch)
            
            cursor.executemany("""
                INSERT INTO documentos_identidad 
                (cliente_id, tipo_documento, numero_documento, fecha_emision, fecha_vencimiento)
                VALUES (%s, %s, %s, %s, %s)
            """, documentos_batch)
            
            conn.commit()
            total_inserted += len(clientes_batch)
            print(f"   ✅ Insertados {total_inserted}/{num_records} clientes...")
            
        except Exception as e:
            conn.rollback()
            print(f"   ❌ Error insertando lote: {e}")
            break
    
    cursor.close()
    return total_inserted

def main():
    print("=" * 60)
    print("🚀 POBLANDO MS1 (PostgreSQL) CON 20,000 CLIENTES")
    print("=" * 60)
    
    conn = create_connection()
    
    # Limpiar tablas existentes
    clear_tables(conn)
    
    # Insertar 20,000 clientes
    total = insert_clientes_batch(conn, num_records=20000, batch_size=1000)
    
    # Verificar
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM clientes;")
    count = cursor.fetchone()[0]
    cursor.close()
    
    print("=" * 60)
    print(f"✅ COMPLETADO: {count} clientes insertados en PostgreSQL")
    print("=" * 60)
    
    conn.close()

if __name__ == "__main__":
    main()
