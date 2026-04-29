"""
Tracer Alumni — UMM
Implementasi pseudocode pencarian multi-platform dengan validasi kesesuaian data.

PSEUDOCODE FLOW:
  FOR setiap alumni:
    1. Buat profil target (nama, prodi, tahun_lulus, kata_kunci)
    2. FOR setiap platform (LinkedIn, GoogleScholar, ResearchGate, Instagram, Facebook):
         hasil = cari_profil(platform, kata_kunci)
         IF hasil → validasi = cek_kesesuaian(hasil, target)
                     IF valid → simpan + BREAK
    3. IF tidak ditemukan → status = "Tidak Ditemukan"
    4. Simpan ke tracer_alumni
  Buat laporan: jumlah ditemukan, distribusi platform, distribusi pekerjaan
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
import sqlite3, os, random, time, hashlib, functools, json
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'tracer-alumni-umm-secret-2024'

BASE_DIR     = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, 'instance')
DB_PATH      = os.path.join(INSTANCE_DIR, 'alumni_system.db')
os.makedirs(INSTANCE_DIR, exist_ok=True)

# ═══════════════════════════════════════════════════
# DATABASE
# ═══════════════════════════════════════════════════

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def hash_pw(pw): return hashlib.sha256(pw.encode()).hexdigest()

def init_db():
    with get_db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'admin',
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS alumni (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nama TEXT NOT NULL,
            nim TEXT,
            tahun_masuk INTEGER,
            tanggal_lulus TEXT,
            fakultas TEXT,
            prodi TEXT,
            universitas TEXT DEFAULT 'Universitas Muhammadiyah Malang',
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS tracer_alumni (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alumni_id INTEGER NOT NULL UNIQUE,
            -- Profil target
            kata_kunci TEXT,
            -- Platform yang ditemukan
            platform_ditemukan TEXT,
            link_profil TEXT,
            -- Data pekerjaan/institusi
            pekerjaan TEXT,
            institusi TEXT,
            lokasi TEXT,
            -- Kontak & sosmed
            email TEXT,
            no_hp TEXT,
            linkedin TEXT,
            instagram TEXT,
            facebook TEXT,
            google_scholar TEXT,
            researchgate TEXT,
            -- Status & metadata
            status TEXT DEFAULT 'Belum Dilacak',
            skor_validasi INTEGER DEFAULT 0,
            catatan_validasi TEXT,
            tahun_update TEXT,
            traced_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (alumni_id) REFERENCES alumni(id)
        );
        CREATE TABLE IF NOT EXISTS trace_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alumni_id INTEGER NOT NULL,
            platform TEXT NOT NULL,
            keyword TEXT,
            hasil TEXT,
            skor_kesesuaian INTEGER DEFAULT 0,
            detail_validasi TEXT,
            status TEXT,
            durasi_ms INTEGER,
            logged_at TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_alumni_nama      ON alumni(nama);
        CREATE INDEX IF NOT EXISTS idx_alumni_fakultas  ON alumni(fakultas);
        CREATE INDEX IF NOT EXISTS idx_tracer_alumni_id ON tracer_alumni(alumni_id);
        CREATE INDEX IF NOT EXISTS idx_log_alumni_id    ON trace_log(alumni_id);
        """)
        conn.execute(
            "INSERT OR IGNORE INTO users (username,password_hash,role) VALUES (?,?,?)",
            ('admin', hash_pw('admin123'), 'admin')
        )

def login_required(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# ═══════════════════════════════════════════════════
# CORE ENGINE — IMPLEMENTASI PSEUDOCODE
# ═══════════════════════════════════════════════════

# Platform dan tingkat keberhasilan realistis
PLATFORMS = [
    {
        'id': 'linkedin',
        'nama': 'LinkedIn',
        'tipe': 'professional',
        'rate_base': 0.42,
        'icon': 'linkedin',
        'warna': '#0a66c2',
        'url_template': 'https://linkedin.com/in/{slug}',
    },
    {
        'id': 'google_scholar',
        'nama': 'Google Scholar',
        'tipe': 'academic',
        'rate_base': 0.18,
        'icon': 'scholar',
        'warna': '#4285f4',
        'url_template': 'https://scholar.google.com/citations?user={slug}',
    },
    {
        'id': 'researchgate',
        'nama': 'ResearchGate',
        'tipe': 'academic',
        'rate_base': 0.14,
        'icon': 'researchgate',
        'warna': '#00ccbb',
        'url_template': 'https://researchgate.net/profile/{slug}',
    },
    {
        'id': 'instagram',
        'nama': 'Instagram',
        'tipe': 'social',
        'rate_base': 0.38,
        'icon': 'instagram',
        'warna': '#e1306c',
        'url_template': 'https://instagram.com/{slug}',
    },
    {
        'id': 'facebook',
        'nama': 'Facebook',
        'tipe': 'social',
        'rate_base': 0.35,
        'icon': 'facebook',
        'warna': '#1877f2',
        'url_template': 'https://facebook.com/{slug}',
    },
]

JOBS = [
    'Software Engineer', 'Data Scientist', 'Product Manager', 'Data Analyst',
    'Dosen', 'Peneliti', 'Backend Developer', 'Frontend Developer',
    'ML Engineer', 'DevOps Engineer', 'Konsultan IT', 'Business Analyst',
    'Guru', 'Kepala Sekolah', 'Dokter', 'Perawat', 'Apoteker',
    'Akuntan', 'Auditor', 'Financial Analyst', 'Tax Consultant',
    'Pengacara', 'Notaris', 'Hakim', 'Jaksa',
    'Wirausaha', 'Founder', 'CEO', 'Direktur',
    'PNS Kemendikbud', 'PNS Kemenkes', 'TNI', 'Polri',
    'Arsitek', 'Civil Engineer', 'Mechanical Engineer',
    'Marketing Manager', 'Brand Strategist', 'Copywriter',
    'Psikolog Klinis', 'HRD Manager', 'Recruiter',
    'Jurnalis', 'Content Creator', 'Desainer Grafis',
]

INSTITUSI = [
    'Tokopedia', 'Gojek', 'Grab', 'Traveloka', 'Shopee', 'Bukalapak', 'Blibli',
    'Telkom Indonesia', 'XL Axiata', 'Indosat', 'BUMN Lainnya',
    'Bank BCA', 'Bank Mandiri', 'Bank BNI', 'Bank BRI',
    'Universitas Muhammadiyah Malang', 'Universitas Brawijaya', 'ITS', 'UI', 'UGM', 'Unair',
    'BRIN', 'LIPI', 'Kementerian Pendidikan', 'Pemkot Malang', 'Pemkab Malang',
    'RS Saiful Anwar', 'RS UMM', 'Puskesmas', 'Klinik Swasta',
    'Accenture', 'Deloitte', 'PwC', 'Ernst & Young', 'KPMG',
    'SMA Negeri', 'SMK Swasta', 'MAN',
    'Startup Lokal', 'Agency Digital', 'Konsultan Independen',
    'PT Semen Indonesia', 'PT Petrokimia', 'PT Pertamina',
]

LOKASI = [
    'Malang, Jawa Timur', 'Surabaya, Jawa Timur', 'Jakarta Selatan, DKI Jakarta',
    'Jakarta Pusat, DKI Jakarta', 'Bandung, Jawa Barat', 'Yogyakarta, DIY',
    'Semarang, Jawa Tengah', 'Bali', 'Sidoarjo, Jawa Timur', 'Pasuruan, Jawa Timur',
    'Batu, Jawa Timur', 'Kediri, Jawa Timur', 'Mojokerto, Jawa Timur',
    'Singapore', 'Kuala Lumpur, Malaysia', 'Melbourne, Australia',
]

JENIS_PEKERJAAN = {
    'PNS': ['Guru', 'Kepala Sekolah', 'Dokter', 'Perawat', 'Jaksa', 'Hakim',
            'TNI', 'Polri', 'PNS Kemendikbud', 'PNS Kemenkes'],
    'Wirausaha': ['Wirausaha', 'Founder', 'CEO', 'Konsultan Independen', 'Content Creator'],
    'Swasta': [],  # default untuk yang tidak masuk PNS/Wirausaha
}

def get_slug(nama):
    """Buat slug URL dari nama."""
    import re
    slug = nama.lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug.strip())
    return slug

def buat_profil_target(alumni):
    """
    PSEUDOCODE STEP 2: Buat profil target pencarian.
    target.nama, target.prodi, target.tahun_lulus, target.kata_kunci
    """
    nama  = alumni['nama'] or ''
    prodi = alumni['prodi'] or ''
    univ  = alumni['universitas'] or 'Universitas Muhammadiyah Malang'
    tahun = str(alumni['tanggal_lulus'] or alumni['tahun_masuk'] or '')

    # Kata kunci = kombinasi nama + prodi + universitas (sesuai pseudocode)
    kata_kunci = f"{nama} {prodi} {univ}".strip()

    return {
        'nama': nama,
        'prodi': prodi,
        'universitas': univ,
        'tahun_lulus': tahun,
        'kata_kunci': kata_kunci,
        'slug': get_slug(nama),
        'nim': alumni.get('nim', ''),
        'fakultas': alumni.get('fakultas', ''),
    }

def cari_profil(platform, target):
    """
    PSEUDOCODE STEP 4: cari_profil(platform, target.kata_kunci)
    Simulasi pencarian per platform dengan delay realistis.
    Return: (hasil_dict | None, durasi_ms)
    """
    t0 = time.time()
    # Simulasi network delay berbeda per platform
    delay_map = {
        'linkedin': (0.08, 0.25),
        'google_scholar': (0.12, 0.30),
        'researchgate': (0.10, 0.28),
        'instagram': (0.06, 0.18),
        'facebook': (0.07, 0.20),
    }
    lo, hi = delay_map.get(platform['id'], (0.05, 0.15))
    time.sleep(random.uniform(lo, hi))

    slug = target['slug']
    rate = platform['rate_base']

    # Faktor boost berdasarkan konteks
    # Alumni akademik lebih mungkin di Scholar/ResearchGate
    prodi_lower = target['prodi'].lower()
    if platform['id'] in ('google_scholar', 'researchgate'):
        if any(k in prodi_lower for k in ['magister', 'doktor', 'pascasarjana', 'peneliti', 'ilmu']):
            rate *= 1.8
        if any(k in prodi_lower for k in ['teknik', 'informatika', 'kedokteran', 'farmasi']):
            rate *= 1.4

    if platform['id'] == 'linkedin':
        if any(k in prodi_lower for k in ['manajemen', 'akuntansi', 'teknik', 'informatika', 'bisnis']):
            rate *= 1.3

    # Roll pencarian
    if random.random() > rate:
        durasi = int((time.time() - t0) * 1000)
        return None, durasi

    # Profil ditemukan — generate data
    hasil = {
        'platform_id': platform['id'],
        'platform_nama': platform['nama'],
        'url': platform['url_template'].format(slug=slug),
        'nama_profil': target['nama'],
        'prodi_profil': target['prodi'] if random.random() > 0.2 else '',
        'universitas_profil': target['universitas'] if random.random() > 0.25 else '',
        'pekerjaan': random.choice(JOBS),
        'institusi': random.choice(INSTITUSI),
        'lokasi': random.choice(LOKASI),
        'tahun_update': str(random.randint(2020, 2025)),
    }

    # Data kontak (probabilistik)
    if random.random() < 0.4:
        hasil['email'] = f"{slug.replace('-','.')}@gmail.com"
    if random.random() < 0.3:
        hasil['no_hp'] = f"08{random.randint(100000000, 999999999)}"

    durasi = int((time.time() - t0) * 1000)
    return hasil, durasi

def cek_kesesuaian_data(hasil, target):
    """
    PSEUDOCODE STEP 4: validasi = cek_kesesuaian_data(hasil, target)
    Cek apakah hasil pencarian benar-benar cocok dengan alumni target.
    Return: (valid: bool, skor: int 0-100, detail: str)
    """
    skor = 0
    detail = []

    # 1. Kesesuaian nama (bobot tertinggi: 50 poin)
    nama_target = target['nama'].lower()
    nama_hasil  = hasil.get('nama_profil', '').lower()
    if nama_target == nama_hasil:
        skor += 50
        detail.append("✓ Nama persis cocok (+50)")
    elif nama_target in nama_hasil or nama_hasil in nama_target:
        skor += 35
        detail.append("✓ Nama sebagian cocok (+35)")
    else:
        # Cek token nama (minimal 2 token sama)
        tok_t = set(nama_target.split())
        tok_h = set(nama_hasil.split())
        overlap = tok_t & tok_h
        if len(overlap) >= 2:
            skor += 20
            detail.append(f"~ Nama token cocok: {', '.join(overlap)} (+20)")
        else:
            detail.append("✗ Nama tidak cocok (+0)")

    # 2. Kesesuaian prodi/institusi akademis (25 poin)
    prodi_target = target['prodi'].lower()
    prodi_hasil  = hasil.get('prodi_profil', '').lower()
    univ_hasil   = hasil.get('universitas_profil', '').lower()

    if prodi_target and prodi_hasil and (prodi_target in prodi_hasil or prodi_hasil in prodi_target):
        skor += 25
        detail.append("✓ Prodi cocok (+25)")
    elif target['universitas'].lower() in univ_hasil or univ_hasil in target['universitas'].lower():
        skor += 15
        detail.append("~ Universitas cocok (+15)")
    else:
        detail.append("✗ Prodi/universitas tidak cocok (+0)")

    # 3. Konsistensi data pekerjaan (15 poin)
    if hasil.get('pekerjaan') and hasil.get('institusi'):
        skor += 15
        detail.append("✓ Data pekerjaan tersedia (+15)")
    elif hasil.get('pekerjaan') or hasil.get('institusi'):
        skor += 8
        detail.append("~ Data pekerjaan sebagian (+8)")

    # 4. Tahun update relevan (10 poin)
    try:
        tahun = int(hasil.get('tahun_update', 0))
        if tahun >= 2020:
            skor += 10
            detail.append(f"✓ Data terbaru {tahun} (+10)")
        elif tahun >= 2015:
            skor += 5
            detail.append(f"~ Data cukup lama {tahun} (+5)")
    except:
        pass

    # Threshold validasi: skor >= 50 dianggap valid
    valid = skor >= 50
    return valid, skor, " | ".join(detail)

def tentukan_jenis_pekerjaan(pekerjaan):
    """Kategorikan jenis pekerjaan dari nama posisi."""
    for jenis, jobs in JENIS_PEKERJAAN.items():
        if pekerjaan in jobs:
            return jenis
    return 'Swasta'

def lacak_alumni(alumni_data):
    """
    IMPLEMENTASI LENGKAP PSEUDOCODE STEPS 1-6 untuk satu alumni.

    Returns:
        dict dengan keys: status, platform_ditemukan, data, logs
    """
    # STEP 1-2: Buat profil target
    target = buat_profil_target(alumni_data)

    logs   = []
    status = 'Tidak Ditemukan'
    data_tersimpan = {}

    # STEP 3-4: FOR setiap platform dalam sumber
    for platform in PLATFORMS:
        # cari_profil(platform, target.kata_kunci)
        hasil, durasi_ms = cari_profil(platform, target)

        if hasil:
            # validasi = cek_kesesuaian_data(hasil, target)
            valid, skor, detail_validasi = cek_kesesuaian_data(hasil, target)

            if valid:
                # simpan_data
                data_tersimpan = {
                    'platform_ditemukan': platform['nama'],
                    'link_profil': hasil['url'],
                    'pekerjaan': hasil.get('pekerjaan'),
                    'institusi': hasil.get('institusi'),
                    'lokasi': hasil.get('lokasi'),
                    'tahun_update': hasil.get('tahun_update'),
                    'email': hasil.get('email'),
                    'no_hp': hasil.get('no_hp'),
                }
                # Set field platform spesifik
                pid = platform['id']
                if pid == 'linkedin':
                    data_tersimpan['linkedin'] = hasil['url']
                elif pid == 'instagram':
                    data_tersimpan['instagram'] = hasil['url']
                elif pid == 'facebook':
                    data_tersimpan['facebook'] = hasil['url']
                elif pid == 'google_scholar':
                    data_tersimpan['google_scholar'] = hasil['url']
                elif pid == 'researchgate':
                    data_tersimpan['researchgate'] = hasil['url']

                logs.append({
                    'platform': platform['nama'],
                    'keyword': target['kata_kunci'],
                    'hasil': 'ditemukan',
                    'skor': skor,
                    'detail': detail_validasi,
                    'status': 'valid_ditemukan',
                    'durasi_ms': durasi_ms,
                })
                status = 'Ditemukan'
                break  # BREAK — sesuai pseudocode
            else:
                # Ditemukan tapi tidak valid (akun berbeda)
                logs.append({
                    'platform': platform['nama'],
                    'keyword': target['kata_kunci'],
                    'hasil': 'ditemukan_tidak_valid',
                    'skor': skor,
                    'detail': detail_validasi,
                    'status': 'invalid',
                    'durasi_ms': durasi_ms,
                })
        else:
            logs.append({
                'platform': platform['nama'],
                'keyword': target['kata_kunci'],
                'hasil': 'tidak_ditemukan',
                'skor': 0,
                'detail': 'Tidak ada profil yang ditemukan di platform ini',
                'status': 'not_found',
                'durasi_ms': durasi_ms,
            })

    # STEP 5: IF status_alumni != "Ditemukan" → "Tidak Ditemukan"
    if status != 'Ditemukan':
        status = 'Tidak Ditemukan'

    return {
        'status': status,
        'target': target,
        'data': data_tersimpan,
        'logs': logs,
    }

def simpan_hasil_ke_db(alumni_id, target, status, data, logs):
    """PSEUDOCODE STEP 6: Simpan hasil pelacakan ke database tracer_alumni."""
    jenis_pekerjaan = None
    if data.get('pekerjaan'):
        jenis_pekerjaan = tentukan_jenis_pekerjaan(data.get('pekerjaan', ''))

    with get_db() as conn:
        conn.execute("DELETE FROM tracer_alumni WHERE alumni_id=?", (alumni_id,))
        conn.execute("""
            INSERT INTO tracer_alumni (
                alumni_id, kata_kunci,
                platform_ditemukan, link_profil,
                pekerjaan, institusi, lokasi,
                email, no_hp,
                linkedin, instagram, facebook,
                google_scholar, researchgate,
                status, skor_validasi, catatan_validasi,
                tahun_update
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            alumni_id,
            target.get('kata_kunci'),
            data.get('platform_ditemukan'),
            data.get('link_profil'),
            data.get('pekerjaan'),
            data.get('institusi'),
            data.get('lokasi'),
            data.get('email'),
            data.get('no_hp'),
            data.get('linkedin'),
            data.get('instagram'),
            data.get('facebook'),
            data.get('google_scholar'),
            data.get('researchgate'),
            status,
            # Skor dari log terakhir yang valid
            next((l['skor'] for l in reversed(logs) if l['status']=='valid_ditemukan'), 0),
            next((l['detail'] for l in reversed(logs) if l['status']=='valid_ditemukan'), None),
            data.get('tahun_update'),
        ))
        # Simpan log per platform
        for log in logs:
            conn.execute("""
                INSERT INTO trace_log (alumni_id, platform, keyword, hasil,
                    skor_kesesuaian, detail_validasi, status, durasi_ms)
                VALUES (?,?,?,?,?,?,?,?)
            """, (
                alumni_id,
                log['platform'],
                log['keyword'],
                log['hasil'],
                log.get('skor', 0),
                log.get('detail', ''),
                log.get('status', ''),
                log.get('durasi_ms', 0),
            ))

# ═══════════════════════════════════════════════════
# AUTH
# ═══════════════════════════════════════════════════

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('index'))
    error = None
    if request.method == 'POST':
        uname = request.form.get('username', '').strip()
        pw    = request.form.get('password', '')
        with get_db() as conn:
            user = conn.execute(
                "SELECT * FROM users WHERE username=? AND password_hash=?",
                (uname, hash_pw(pw))
            ).fetchone()
        if user:
            session['user_id']  = user['id']
            session['username'] = user['username']
            session['role']     = user['role']
            return redirect(url_for('index'))
        error = 'Username atau password salah.'
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ═══════════════════════════════════════════════════
# DASHBOARD
# ═══════════════════════════════════════════════════

@app.route('/')
@login_required
def index():
    with get_db() as conn:
        ta = conn.execute("SELECT COUNT(*) FROM alumni").fetchone()[0]
        td = conn.execute("SELECT COUNT(*) FROM tracer_alumni WHERE status='Ditemukan'").fetchone()[0]
        tn = conn.execute("SELECT COUNT(*) FROM tracer_alumni WHERE status='Tidak Ditemukan'").fetchone()[0]
        tb = ta - td - tn

        fak = conn.execute("""
            SELECT fakultas, COUNT(*) c FROM alumni
            WHERE fakultas IS NOT NULL GROUP BY fakultas ORDER BY c DESC LIMIT 8
        """).fetchall()

        plt_stats = conn.execute("""
            SELECT platform_ditemukan, COUNT(*) c FROM tracer_alumni
            WHERE status='Ditemukan' AND platform_ditemukan IS NOT NULL
            GROUP BY platform_ditemukan ORDER BY c DESC
        """).fetchall()

        jp_stats = conn.execute("""
            SELECT
                CASE
                    WHEN pekerjaan IN ('Guru','Kepala Sekolah','Dokter','Perawat','Jaksa',
                        'Hakim','TNI','Polri','PNS Kemendikbud','PNS Kemenkes') THEN 'PNS'
                    WHEN pekerjaan IN ('Wirausaha','Founder','CEO','Konsultan Independen','Content Creator') THEN 'Wirausaha'
                    WHEN pekerjaan IS NOT NULL THEN 'Swasta'
                    ELSE NULL
                END as jenis,
                COUNT(*) c
            FROM tracer_alumni
            WHERE status='Ditemukan'
            GROUP BY jenis HAVING jenis IS NOT NULL
        """).fetchall()

        recent = conn.execute("""
            SELECT a.nama, a.prodi, a.fakultas, t.status, t.pekerjaan,
                   t.institusi, t.platform_ditemukan, t.traced_at
            FROM tracer_alumni t JOIN alumni a ON t.alumni_id=a.id
            ORDER BY t.traced_at DESC LIMIT 10
        """).fetchall()

    coverage = round((td + tn) / ta * 100, 1) if ta > 0 else 0
    return render_template('index.html',
        total_alumni=ta, total_ditemukan=td, total_tidak=tn, total_belum=tb,
        coverage=coverage, fak_stats=fak, plt_stats=plt_stats,
        jp_stats=jp_stats, recent=recent)

# ═══════════════════════════════════════════════════
# DATA ALUMNI
# ═══════════════════════════════════════════════════

@app.route('/alumni')
@login_required
def alumni_list():
    q    = request.args.get('q', '')
    fak  = request.args.get('fakultas', '')
    stat = request.args.get('status', '')
    page = max(1, int(request.args.get('page', 1)))
    per_page = 50

    sql    = """SELECT a.*, t.status as t_status, t.platform_ditemukan, t.pekerjaan, t.institusi
                FROM alumni a LEFT JOIN tracer_alumni t ON a.id=t.alumni_id WHERE 1=1"""
    params = []
    if q:    sql += " AND a.nama LIKE ?"; params.append(f'%{q}%')
    if fak:  sql += " AND a.fakultas=?";  params.append(fak)
    if stat == 'ditemukan': sql += " AND t.status='Ditemukan'"
    elif stat == 'tidak':   sql += " AND t.status='Tidak Ditemukan'"
    elif stat == 'belum':   sql += " AND t.status IS NULL"

    with get_db() as conn:
        total = conn.execute(f"SELECT COUNT(*) FROM ({sql})", params).fetchone()[0]
        rows  = conn.execute(
            sql + f" ORDER BY a.nama LIMIT {per_page} OFFSET {(page-1)*per_page}", params
        ).fetchall()
        fakults = conn.execute(
            "SELECT DISTINCT fakultas FROM alumni WHERE fakultas IS NOT NULL ORDER BY fakultas"
        ).fetchall()

    return render_template('alumni.html',
        alumni=rows, fakults=fakults, q=q, fak_filter=fak, stat_filter=stat,
        page=page, total_pages=(total+per_page-1)//per_page,
        total_rows=total, per_page=per_page)

@app.route('/alumni/add', methods=['GET', 'POST'])
@login_required
def add_alumni():
    if request.method == 'POST':
        d = request.form
        with get_db() as conn:
            conn.execute("""INSERT INTO alumni (nama,nim,tahun_masuk,tanggal_lulus,fakultas,prodi,universitas)
                            VALUES (?,?,?,?,?,?,?)""",
                (d['nama'], d.get('nim'), d.get('tahun_masuk') or None,
                 d.get('tanggal_lulus'), d.get('fakultas'), d.get('prodi'),
                 d.get('universitas', 'Universitas Muhammadiyah Malang')))
        flash('Alumni berhasil ditambahkan', 'success')
        return redirect(url_for('alumni_list'))
    with get_db() as conn:
        fakults = conn.execute("SELECT DISTINCT fakultas FROM alumni WHERE fakultas IS NOT NULL ORDER BY fakultas").fetchall()
        prodis  = conn.execute("SELECT DISTINCT prodi FROM alumni WHERE prodi IS NOT NULL ORDER BY prodi").fetchall()
    return render_template('add_alumni.html', fakults=fakults, prodis=prodis)

@app.route('/alumni/<int:id>/detail')
@login_required
def alumni_detail(id):
    with get_db() as conn:
        a = conn.execute("SELECT * FROM alumni WHERE id=?", (id,)).fetchone()
        t = conn.execute("SELECT * FROM tracer_alumni WHERE alumni_id=?", (id,)).fetchone()
        logs = conn.execute(
            "SELECT * FROM trace_log WHERE alumni_id=? ORDER BY logged_at DESC LIMIT 20", (id,)
        ).fetchall()
    if not a: return "Not found", 404
    return render_template('detail.html', a=a, t=t, logs=logs, platforms=PLATFORMS)

@app.route('/alumni/<int:id>/edit-tracer', methods=['POST'])
@login_required
def edit_tracer(id):
    d = request.form
    with get_db() as conn:
        conn.execute("DELETE FROM tracer_alumni WHERE alumni_id=?", (id,))
        conn.execute("""INSERT INTO tracer_alumni (
            alumni_id, platform_ditemukan, link_profil, pekerjaan, institusi, lokasi,
            email, no_hp, linkedin, instagram, facebook, google_scholar, researchgate,
            status, tahun_update, kata_kunci)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (id, d.get('platform_ditemukan'), d.get('link_profil'),
             d.get('pekerjaan'), d.get('institusi'), d.get('lokasi'),
             d.get('email'), d.get('no_hp'), d.get('linkedin'),
             d.get('instagram'), d.get('facebook'),
             d.get('google_scholar'), d.get('researchgate'),
             'Ditemukan', d.get('tahun_update'), d.get('kata_kunci')))
    return jsonify({'success': True})

@app.route('/alumni/delete/<int:id>', methods=['POST'])
@login_required
def delete_alumni(id):
    with get_db() as conn:
        conn.execute("DELETE FROM trace_log WHERE alumni_id=?", (id,))
        conn.execute("DELETE FROM tracer_alumni WHERE alumni_id=?", (id,))
        conn.execute("DELETE FROM alumni WHERE id=?", (id,))
    return jsonify({'success': True})

# ═══════════════════════════════════════════════════
# TRACER — HALAMAN & API
# ═══════════════════════════════════════════════════

@app.route('/tracer')
@login_required
def tracer():
    with get_db() as conn:
        total_alumni = conn.execute("SELECT COUNT(*) FROM alumni").fetchone()[0]
        total_traced = conn.execute("SELECT COUNT(*) FROM tracer_alumni").fetchone()[0]
        total_found  = conn.execute("SELECT COUNT(*) FROM tracer_alumni WHERE status='Ditemukan'").fetchone()[0]
        history = conn.execute("""
            SELECT a.nama, a.prodi, t.status, t.platform_ditemukan,
                   t.pekerjaan, t.institusi, t.skor_validasi, t.traced_at
            FROM tracer_alumni t JOIN alumni a ON t.alumni_id=a.id
            ORDER BY t.traced_at DESC LIMIT 25
        """).fetchall()
    return render_template('tracer.html',
        history=history, total_alumni=total_alumni,
        total_traced=total_traced, total_found=total_found,
        platforms=PLATFORMS)

@app.route('/api/search-alumni')
@login_required
def search_alumni_api():
    q = request.args.get('q', '').strip()
    if len(q) < 2:
        return jsonify([])
    with get_db() as conn:
        rows = conn.execute(
            """SELECT a.id, a.nama, a.prodi, a.fakultas, a.nim, a.tahun_masuk, a.tanggal_lulus,
                      t.status as t_status
               FROM alumni a LEFT JOIN tracer_alumni t ON a.id=t.alumni_id
               WHERE a.nama LIKE ? LIMIT 15""",
            (f'%{q}%',)
        ).fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/api/trace/<int:alumni_id>', methods=['POST'])
@login_required
def trace_alumni(alumni_id):
    """
    API endpoint untuk lacak satu alumni.
    Mengimplementasikan pseudocode steps 1-6 secara penuh.
    """
    with get_db() as conn:
        alumni = conn.execute("SELECT * FROM alumni WHERE id=?", (alumni_id,)).fetchone()
    if not alumni:
        return jsonify({'error': 'Alumni tidak ditemukan'}), 404

    # Jalankan pipeline pelacakan
    result = lacak_alumni(dict(alumni))

    # Simpan ke database
    simpan_hasil_ke_db(
        alumni_id,
        result['target'],
        result['status'],
        result['data'],
        result['logs']
    )

    return jsonify({
        'status': result['status'],
        'alumni': alumni['nama'],
        'target': result['target'],
        'data': result['data'],
        'logs': result['logs'],
        'platform_count': len(PLATFORMS),
    })

@app.route('/api/trace-batch', methods=['POST'])
@login_required
def trace_batch():
    """
    Batch tracing: FOR setiap alumni dalam batch → jalankan pipeline.
    Max 50 per request.
    """
    payload = request.get_json() or {}
    ids     = payload.get('ids', [])[:50]
    results = []

    with get_db() as conn:
        for aid in ids:
            alumni = conn.execute("SELECT * FROM alumni WHERE id=?", (aid,)).fetchone()
            if not alumni:
                continue
            result = lacak_alumni(dict(alumni))
            simpan_hasil_ke_db(aid, result['target'], result['status'], result['data'], result['logs'])
            results.append({
                'id': aid,
                'nama': alumni['nama'],
                'status': result['status'],
                'platform': result['data'].get('platform_ditemukan'),
                'pekerjaan': result['data'].get('pekerjaan'),
            })

    found = sum(1 for r in results if r['status'] == 'Ditemukan')
    return jsonify({'results': results, 'count': len(results), 'found': found})

@app.route('/api/all-alumni-ids')
@login_required
def get_all_alumni_ids():
    """Return semua ID alumni yang belum dilacak (atau semua jika force=1)."""
    force = request.args.get('force', '0') == '1'
    with get_db() as conn:
        if force:
            rows = conn.execute("SELECT id FROM alumni ORDER BY id").fetchall()
        else:
            rows = conn.execute("""
                SELECT a.id FROM alumni a
                LEFT JOIN tracer_alumni t ON a.id = t.alumni_id
                WHERE t.alumni_id IS NULL
                ORDER BY a.id
            """).fetchall()
        total = conn.execute("SELECT COUNT(*) FROM alumni").fetchone()[0]
    ids = [r[0] for r in rows]
    return jsonify({'ids': ids, 'count': len(ids), 'total': total})

@app.route('/api/trace-all-stream')
@login_required
def trace_all_stream():
    """
    Server-Sent Events stream: lacak SEMUA alumni satu per satu,
    kirim update progress ke frontend secara realtime.
    Query params:
      - force=1  → lacak ulang yang sudah dilacak
      - batch_size=N → jumlah per chunk (default 50)
    """
    from flask import Response, stream_with_context

    force      = request.args.get('force', '0') == '1'
    batch_size = min(int(request.args.get('batch_size', 50)), 100)

    def generate():
        with get_db() as conn:
            if force:
                rows = conn.execute("SELECT id FROM alumni ORDER BY id").fetchall()
            else:
                rows = conn.execute("""
                    SELECT a.id FROM alumni a
                    LEFT JOIN tracer_alumni t ON a.id = t.alumni_id
                    WHERE t.alumni_id IS NULL
                    ORDER BY a.id
                """).fetchall()
            total = len(rows)

        if total == 0:
            yield f"data: {json.dumps({'type':'done','found':0,'not_found':0,'total':0,'processed':0})}\n\n"
            return

        found     = 0
        not_found = 0
        processed = 0

        # Stream: kirim status awal
        yield f"data: {json.dumps({'type':'start','total':total})}\n\n"

        for i in range(0, total, batch_size):
            chunk_ids = [r[0] for r in rows[i:i+batch_size]]

            with get_db() as conn:
                for aid in chunk_ids:
                    alumni = conn.execute("SELECT * FROM alumni WHERE id=?", (aid,)).fetchone()
                    if not alumni:
                        continue

                    result = lacak_alumni(dict(alumni))
                    simpan_hasil_ke_db(
                        aid, result['target'], result['status'],
                        result['data'], result['logs']
                    )

                    processed += 1
                    if result['status'] == 'Ditemukan':
                        found += 1
                    else:
                        not_found += 1

                    # Kirim update per alumni
                    pct = round(processed / total * 100, 1)
                    payload = {
                        'type':      'progress',
                        'processed': processed,
                        'total':     total,
                        'pct':       pct,
                        'found':     found,
                        'not_found': not_found,
                        'nama':      alumni['nama'],
                        'status':    result['status'],
                        'platform':  result['data'].get('platform_ditemukan', ''),
                    }
                    yield f"data: {json.dumps(payload)}\n\n"

        # Done
        yield f"data: {json.dumps({'type':'done','found':found,'not_found':not_found,'total':total,'processed':processed})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
        }
    )

@app.route('/api/trace-log/<int:alumni_id>')
@login_required
def get_trace_log(alumni_id):
    with get_db() as conn:
        logs = conn.execute(
            "SELECT * FROM trace_log WHERE alumni_id=? ORDER BY logged_at DESC LIMIT 30", (alumni_id,)
        ).fetchall()
    return jsonify([dict(l) for l in logs])

# ═══════════════════════════════════════════════════
# LAPORAN — PSEUDOCODE STEP 7
# ═══════════════════════════════════════════════════

@app.route('/laporan')
@login_required
def laporan():
    """
    PSEUDOCODE STEP 7: Buat laporan
    - Jumlah alumni ditemukan
    - Sumber platform
    - Distribusi pekerjaan
    """
    with get_db() as conn:
        ta = conn.execute("SELECT COUNT(*) FROM alumni").fetchone()[0]
        td = conn.execute("SELECT COUNT(*) FROM tracer_alumni WHERE status='Ditemukan'").fetchone()[0]

        # Distribusi per platform (sumber pencarian)
        plt_stats = conn.execute("""
            SELECT platform_ditemukan, COUNT(*) c FROM tracer_alumni
            WHERE status='Ditemukan' AND platform_ditemukan IS NOT NULL
            GROUP BY platform_ditemukan ORDER BY c DESC
        """).fetchall()

        # Distribusi pekerjaan
        job_stats = conn.execute("""
            SELECT pekerjaan, COUNT(*) c FROM tracer_alumni
            WHERE status='Ditemukan' AND pekerjaan IS NOT NULL
            GROUP BY pekerjaan ORDER BY c DESC LIMIT 12
        """).fetchall()

        # Jenis pekerjaan (PNS/Swasta/Wirausaha)
        jp_stats = conn.execute("""
            SELECT
                CASE
                    WHEN pekerjaan IN ('Guru','Kepala Sekolah','Dokter','Perawat','Jaksa',
                        'Hakim','TNI','Polri','PNS Kemendikbud','PNS Kemenkes') THEN 'PNS'
                    WHEN pekerjaan IN ('Wirausaha','Founder','CEO','Konsultan Independen','Content Creator') THEN 'Wirausaha'
                    WHEN pekerjaan IS NOT NULL THEN 'Swasta'
                    ELSE NULL
                END as jenis, COUNT(*) c
            FROM tracer_alumni WHERE status='Ditemukan'
            GROUP BY jenis HAVING jenis IS NOT NULL ORDER BY c DESC
        """).fetchall()

        # Distribusi per fakultas
        fak_stats = conn.execute("""
            SELECT a.fakultas, COUNT(*) c FROM alumni a
            WHERE a.fakultas IS NOT NULL GROUP BY a.fakultas ORDER BY c DESC
        """).fetchall()

        # Top institusi
        inst_stats = conn.execute("""
            SELECT institusi, COUNT(*) c FROM tracer_alumni
            WHERE status='Ditemukan' AND institusi IS NOT NULL
            GROUP BY institusi ORDER BY c DESC LIMIT 10
        """).fetchall()

        # Distribusi lokasi
        lok_stats = conn.execute("""
            SELECT lokasi, COUNT(*) c FROM tracer_alumni
            WHERE status='Ditemukan' AND lokasi IS NOT NULL
            GROUP BY lokasi ORDER BY c DESC LIMIT 10
        """).fetchall()

        # Statistik validasi (skor rata-rata)
        val_stats = conn.execute("""
            SELECT AVG(skor_validasi), MIN(skor_validasi), MAX(skor_validasi)
            FROM tracer_alumni WHERE status='Ditemukan'
        """).fetchone()

        # Log stats per platform
        log_platform = conn.execute("""
            SELECT platform,
                   COUNT(*) total,
                   SUM(CASE WHEN status='valid_ditemukan' THEN 1 ELSE 0 END) valid,
                   SUM(CASE WHEN status='invalid' THEN 1 ELSE 0 END) invalid,
                   AVG(durasi_ms) avg_ms
            FROM trace_log
            GROUP BY platform ORDER BY valid DESC
        """).fetchall()

        # Top prodi
        prodi_stats = conn.execute("""
            SELECT prodi, COUNT(*) c FROM alumni WHERE prodi IS NOT NULL
            GROUP BY prodi ORDER BY c DESC LIMIT 10
        """).fetchall()

    coverage = round(td / ta * 100, 1) if ta > 0 else 0
    return render_template('laporan.html',
        total_alumni=ta, total_ditemukan=td, coverage=coverage,
        plt_stats=plt_stats, job_stats=job_stats, jp_stats=jp_stats,
        fak_stats=fak_stats, inst_stats=inst_stats, lok_stats=lok_stats,
        val_stats=val_stats, log_platform=log_platform, prodi_stats=prodi_stats)

# ═══════════════════════════════════════════════════
# SETTINGS / USER MANAGEMENT
# ═══════════════════════════════════════════════════

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    msg = None
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'change_password':
            old = request.form.get('old_password', '')
            new = request.form.get('new_password', '')
            with get_db() as conn:
                u = conn.execute("SELECT * FROM users WHERE id=? AND password_hash=?",
                                 (session['user_id'], hash_pw(old))).fetchone()
                if u:
                    conn.execute("UPDATE users SET password_hash=? WHERE id=?",
                                 (hash_pw(new), session['user_id']))
                    msg = ('success', 'Password berhasil diubah.')
                else:
                    msg = ('error', 'Password lama salah.')
        elif action == 'add_user' and session.get('role') == 'admin':
            uname = request.form.get('new_username', '').strip()
            pw    = request.form.get('new_password', '')
            role  = request.form.get('new_role', 'admin')
            try:
                with get_db() as conn:
                    conn.execute("INSERT INTO users (username,password_hash,role) VALUES (?,?,?)",
                                 (uname, hash_pw(pw), role))
                msg = ('success', f'User {uname} berhasil ditambahkan.')
            except:
                msg = ('error', 'Username sudah digunakan.')
    with get_db() as conn:
        users = conn.execute("SELECT id,username,role,created_at FROM users").fetchall()
    return render_template('settings.html', users=users, msg=msg)

@app.route('/users/delete/<int:uid>', methods=['POST'])
@login_required
def delete_user(uid):
    if session.get('role') != 'admin' or uid == session['user_id']:
        return jsonify({'success': False})
    with get_db() as conn:
        conn.execute("DELETE FROM users WHERE id=?", (uid,))
    return jsonify({'success': True})

if __name__ == '__main__':
    init_db()
    app.run(debug=True)

# ═══════════════════════════════════════════════════
# JINJA HELPERS
# ═══════════════════════════════════════════════════
@app.template_global()
def platform_icon(icon_id):
    icons = {
        'linkedin':    '<svg viewBox="0 0 24 24" fill="currentColor" width="14" height="14"><path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6zM2 9h4v12H2z"/><circle cx="4" cy="4" r="2"/></svg>',
        'scholar':     '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>',
        'researchgate':'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><circle cx="12" cy="12" r="10"/><path d="M9 9h4a3 3 0 0 1 0 6h-4v-6zM13 15v3"/></svg>',
        'instagram':   '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><rect x="2" y="2" width="20" height="20" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.5" cy="6.5" r="1" fill="currentColor" stroke="none"/></svg>',
        'facebook':    '<svg viewBox="0 0 24 24" fill="currentColor" width="14" height="14"><path d="M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z"/></svg>',
    }
    return icons.get(icon_id, '')
