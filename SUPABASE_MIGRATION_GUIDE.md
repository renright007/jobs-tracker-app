# 🗄️ Supabase Migration Guide

Complete guide to migrate your SQLite data to Supabase PostgreSQL for cloud deployment.

## 📋 Pre-Migration Checklist

### Step 1: Clean Existing Supabase Tables

Since you have existing tables with phony data, delete them first:

1. **Go to Supabase Dashboard**
   - Visit: https://supabase.com/dashboard
   - Navigate to your project: `hnjcdsihsocxlmktjfpl`

2. **Open SQL Editor**
   - Click "SQL Editor" in the left sidebar
   - Click "New query"

3. **Delete Existing Tables**
   
   Copy and paste this SQL to clean your database:

   ```sql
   -- Delete tables in correct order (foreign key constraints)
   DROP TABLE IF EXISTS career_goals CASCADE;
   DROP TABLE IF EXISTS user_profile CASCADE;
   DROP TABLE IF EXISTS documents CASCADE;  
   DROP TABLE IF EXISTS jobs CASCADE;
   DROP TABLE IF EXISTS users CASCADE;
   
   -- Verify tables are deleted
   SELECT table_name FROM information_schema.tables 
   WHERE table_schema = 'public' 
   AND table_type = 'BASE TABLE';
   ```

   ✅ **Expected Result:** Should return empty or only system tables.

### Step 2: Create Fresh Tables

Run this SQL to create the correct schema:

```sql
-- Create users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    email TEXT UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create jobs table
CREATE TABLE jobs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    company_name TEXT,
    job_title TEXT,
    job_description TEXT,
    application_url TEXT,
    status TEXT,
    sentiment TEXT,
    notes TEXT,
    date_added TEXT,
    location TEXT,
    salary TEXT,
    applied_date TEXT
);

-- Create documents table
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    document_name TEXT,
    document_type TEXT,
    upload_date TEXT,
    file_path TEXT,
    document_content TEXT,
    preferred_resume INTEGER DEFAULT 0
);

-- Create user_profile table
CREATE TABLE user_profile (
    id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    selected_resume TEXT,
    created_date TEXT,
    last_updated_date TEXT
);

-- Create career_goals table
CREATE TABLE career_goals (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    goals TEXT,
    submission_date TEXT
);

-- Verify tables created
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_type = 'BASE TABLE'
ORDER BY table_name;
```

✅ **Expected Result:** Should list 5 tables: `career_goals`, `documents`, `jobs`, `user_profile`, `users`

## 🚀 Migration Steps

### Step 3: Import Your Real Data

Now that you have clean tables, import your SQLite data:

```bash
# Make sure you're in your project directory
cd /Users/robertenright63/jobs_apps_reworked

# Run the import script
python3 import_to_supabase.py
```

✅ **Expected Output:**
```
📁 Using export file: sqlite_export_20250805_145534.json
🚀 Importing data to Supabase...
📤 Importing 4 records to users...
  ✅ Batch 1: 4 records inserted
✅ Successfully imported 4 records to users
📤 Importing 32 records to jobs...
  ✅ Batch 1: 32 records inserted
✅ Successfully imported 32 records to jobs
📤 Importing 7 records to documents...
  ✅ Batch 1: 7 records inserted
✅ Successfully imported 7 records to documents
📤 Importing 1 records to user_profile...
  ✅ Batch 1: 1 records inserted
✅ Successfully imported 1 records to user_profile
📤 Importing 6 records to career_goals...
  ✅ Batch 1: 6 records inserted
✅ Successfully imported 6 records to career_goals

🔍 Verifying import...
  ✅ users: 4 records
  ✅ jobs: 32 records
  ✅ documents: 7 records
  ✅ user_profile: 1 records
  ✅ career_goals: 6 records

✅ Migration completed successfully!
🌐 Your app can now use Supabase in cloud deployment
```

### Step 4: Test Local App (Still Uses SQLite)

Your local app should continue working unchanged:

```bash
# Test local app
python3 -m streamlit run app.py
```

Should show: `💾 SQLite - Local Database` in the status.

### Step 5: Deploy to Streamlit Cloud

Now your app will automatically use Supabase in the cloud:

1. **Push to GitHub** (already done):
   ```bash
   git push origin main
   ```

2. **Redeploy on Streamlit Cloud**
   - Go to your Streamlit Cloud dashboard
   - Reboot your app or create new deployment
   - Should deploy in 1-2 minutes with Python 3.11

3. **Verify Cloud Deployment**
   - App should show: `🌐 Supabase (PostgreSQL) - Cloud Database`
   - All your data should be preserved (users, jobs, documents, etc.)
   - No more SQLite read-only filesystem errors!

## 🔧 Troubleshooting

### Import Fails
- Check Supabase credentials in secrets
- Verify tables were created successfully
- Check for foreign key constraint errors

### App Shows SQLite in Cloud
- Verify SUPABASE_URL is in Streamlit Cloud secrets
- Check that supabase package installed correctly
- Look at cloud logs for import errors

### Data Missing
- Check import script output for errors
- Verify export file contains your data
- Run verification query in Supabase SQL Editor

### Verification Queries

Check your data in Supabase SQL Editor:

```sql
-- Count records
SELECT 'users' as table_name, COUNT(*) as count FROM users
UNION ALL
SELECT 'jobs', COUNT(*) FROM jobs  
UNION ALL
SELECT 'documents', COUNT(*) FROM documents
UNION ALL  
SELECT 'user_profile', COUNT(*) FROM user_profile
UNION ALL
SELECT 'career_goals', COUNT(*) FROM career_goals;

-- Sample your data
SELECT username, email FROM users LIMIT 3;
SELECT company_name, job_title FROM jobs LIMIT 3;
SELECT document_name, document_type FROM documents LIMIT 3;
```

## ✅ Success Indicators

**Local Development:**
- ✅ App runs with `💾 SQLite - Local Database`
- ✅ All existing functionality works
- ✅ Data preserved locally

**Cloud Deployment:**  
- ✅ App deploys without SQLite errors
- ✅ Shows `🌐 Supabase (PostgreSQL) - Cloud Database`
- ✅ Users can log in with existing accounts
- ✅ All jobs, documents, and career goals visible
- ✅ Preferred resume functionality works
- ✅ Multi-user support enabled

---

🎯 **Your app is now ready for production cloud deployment with persistent database storage!**