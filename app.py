from flask import Flask, render_template, abort, redirect, url_for, session, flash, request
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)
app.secret_key = 'oven_and_dough_rahasia_banget'

# Konfigurasi Database SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bakery.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'admin123'

# Membuat Model / Tabel Database
class Kue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nama = db.Column(db.String(100), nullable=False)
    harga = db.Column(db.String(50), nullable=False)
    harga_int = db.Column(db.Integer, nullable=False)
    kategori = db.Column(db.String(50), nullable=False)
    rating = db.Column(db.String(10), default="5.0")
    terjual = db.Column(db.Integer, default=0)
    deskripsi = db.Column(db.Text, nullable=False)
    gambar = db.Column(db.String(255), nullable=False)

# Auto-buat database dan isi data awal jika masih kosong
with app.app_context():
    db.create_all()
    if not Kue.query.first():
        data_awal = [
            Kue(nama="Red Velvet Cake", harga="Rp 150.000", harga_int=150000, kategori="Signature", rating="4.9", terjual=340, deskripsi="Kue Red Velvet lembut dengan cream cheese frosting otentik. Cocok untuk perayaan ulang tahun.", gambar="https://images.unsplash.com/photo-1586788224331-91284a51448f?auto=format&fit=crop&w=800&q=80"),
            Kue(nama="Tiramisu Klasik", harga="Rp 180.000", harga_int=180000, kategori="Premium", rating="4.8", terjual=285, deskripsi="Paduan kopi espresso pekat, biskuit ladyfinger, dan keju mascarpone premium dari Italia.", gambar="https://images.unsplash.com/photo-1571115177098-24ec42ed204d?auto=format&fit=crop&w=800&q=80"),
            Kue(nama="Chocolate Fudge", harga="Rp 165.000", harga_int=165000, kategori="Bestseller", rating="5.0", terjual=512, deskripsi="Kue cokelat pekat lumer yang menggugah selera. Dibuat dengan dark chocolate 70% asli Belgia.", gambar="https://images.unsplash.com/photo-1578985545062-69928b1d9587?auto=format&fit=crop&w=800&q=80"),
            Kue(nama="Matcha Mille Crepes", harga="Rp 190.000", harga_int=190000, kategori="Premium", rating="4.7", terjual=198, deskripsi="Berlapis-lapis crepe tipis dengan krim matcha khas Uji, Kyoto. Manisnya pas, dengan sentuhan sedikit pahit teh hijau yang elegan.", gambar="https://images.unsplash.com/photo-1464349095431-e9a21285b5f3?auto=format&fit=crop&w=800&q=80")
        ]
        db.session.bulk_save_objects(data_awal)
        db.session.commit()

# ================= PUBLIC ROUTES ================= #
@app.route('/')
def home():
    kata_kunci = request.args.get('q')
    kategori_filter = request.args.get('kategori')
    
    query = Kue.query
    if kata_kunci:
        query = query.filter((Kue.nama.ilike(f'%{kata_kunci}%')) | (Kue.kategori.ilike(f'%{kata_kunci}%')))
    if kategori_filter:
        query = query.filter(Kue.kategori.ilike(kategori_filter))
        
    hasil = query.all()
    return render_template('index.html', produk=hasil, kata_kunci=kata_kunci, kategori_aktif=kategori_filter)

@app.route('/kue/<int:kue_id>')
def detail_kue(kue_id):
    kue_terpilih = Kue.query.get_or_404(kue_id)
    semua_kue = Kue.query.all()
    return render_template('detail.html', kue=kue_terpilih, semua_kue=semua_kue)

@app.route('/kontak')
def kontak(): return render_template('kontak.html')

# ================= CART ROUTES ================= #
@app.route('/tambah-keranjang/<int:kue_id>', methods=['POST'])
def tambah_keranjang(kue_id):
    if 'keranjang' not in session: session['keranjang'] = []
    kue = Kue.query.get_or_404(kue_id)
        
    for item in session['keranjang']:
        if item['id'] == kue_id:
            item['qty'] += 1
            session.modified = True
            flash(f"Jumlah {kue.nama} ditambah!", "success")
            return redirect(url_for('detail_kue', kue_id=kue_id))
            
    session['keranjang'].append({
        'id': kue.id, 'nama': kue.nama, 'harga': kue.harga, 
        'harga_int': kue.harga_int, 'qty': 1, 'gambar': kue.gambar
    })
    session.modified = True
    flash(f"{kue.nama} masuk ke keranjang!", "success")
    return redirect(url_for('detail_kue', kue_id=kue_id))

@app.route('/keranjang')
def halaman_keranjang():
    keranjang = session.get('keranjang', [])
    total_rp = f"Rp {sum(i['harga_int'] * i['qty'] for i in keranjang):,}".replace(',', '.')
    return render_template('keranjang.html', keranjang=keranjang, total_rp=total_rp)

@app.route('/kosongkan-keranjang')
def kosongkan_keranjang():
    session.pop('keranjang', None)
    flash("Keranjang dikosongkan.", "info")
    return redirect(url_for('halaman_keranjang'))

# ================= LOGIN & DASHBOARD ================= #
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'admin_logged_in' in session: return redirect(url_for('dashboard'))
    if request.method == 'POST':
        if request.form.get('username') == ADMIN_USERNAME and request.form.get('password') == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            flash('Berhasil login.', 'success')
            return redirect(url_for('dashboard'))
        flash('Username/Password salah!', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    flash('Anda telah logout.', 'info')
    return redirect(url_for('home'))

@app.route('/dashboard')
def dashboard():
    if 'admin_logged_in' not in session: return redirect(url_for('login'))
    semua_kue = Kue.query.all()
    terjual = sum(k.terjual for k in semua_kue)
    return render_template('dashboard.html', produk=semua_kue, total=len(semua_kue), terjual=terjual)

# ================= CRUD FITUR ADMIN ================= #
@app.route('/admin/tambah', methods=['GET', 'POST'])
def tambah_produk():
    if 'admin_logged_in' not in session: return redirect(url_for('login'))
    if request.method == 'POST':
        harga_int = int(request.form.get('harga').replace('.', '').replace('Rp', '').strip())
        kue_baru = Kue(
            nama=request.form.get('nama'),
            harga=f"Rp {harga_int:,}".replace(',', '.'),
            harga_int=harga_int,
            kategori=request.form.get('kategori'),
            deskripsi=request.form.get('deskripsi'),
            gambar=request.form.get('gambar')
        )
        db.session.add(kue_baru)
        db.session.commit()
        flash('Produk baru berhasil disimpan ke Database!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('form_kue.html', aksi='Tambah', kue=None)

@app.route('/admin/edit/<int:kue_id>', methods=['GET', 'POST'])
def edit_produk(kue_id):
    if 'admin_logged_in' not in session: return redirect(url_for('login'))
    kue_edit = Kue.query.get_or_404(kue_id)
    
    if request.method == 'POST':
        harga_int = int(request.form.get('harga').replace('.', '').replace('Rp', '').strip())
        kue_edit.nama = request.form.get('nama')
        kue_edit.harga = f"Rp {harga_int:,}".replace(',', '.')
        kue_edit.harga_int = harga_int
        kue_edit.kategori = request.form.get('kategori')
        kue_edit.deskripsi = request.form.get('deskripsi')
        kue_edit.gambar = request.form.get('gambar')
        
        db.session.commit()
        flash(f'Data produk {kue_edit.nama} berhasil diupdate!', 'success')
        return redirect(url_for('dashboard'))
        
    return render_template('form_kue.html', aksi='Edit', kue=kue_edit)

@app.route('/admin/hapus/<int:kue_id>', methods=['POST'])
def hapus_produk(kue_id):
    if 'admin_logged_in' not in session: return redirect(url_for('login'))
    kue_hapus = Kue.query.get_or_404(kue_id)
    db.session.delete(kue_hapus)
    db.session.commit()
    flash(f'Produk {kue_hapus.nama} berhasil dihapus dari Database.', 'success')
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(debug=True)