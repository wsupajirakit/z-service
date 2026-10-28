import re

with open("dash/src/App.tsx", "r") as f:
    content = f.read()

# 1. ExportView states
target_export_state = """
function ExportView() {
  const [interval, setInterval] = useState('4h');
"""
replacement_export_state = """
function ExportView() {
  const [watchlists, setWatchlists] = useState<Record<string, any[]>>({});
  const [selectedWatchlist, setSelectedWatchlist] = useState('All Symbols');

  useEffect(() => {
    fetchWatchlists();
  }, []);

  const fetchWatchlists = async () => {
    try {
      const res = await axios.get(`${API_BASE}/api/watchlist`);
      setWatchlists(res.data);
    } catch (e) {
      console.error('Failed to fetch watchlists', e);
    }
  };

  const [interval, setInterval] = useState('4h');
"""
content = content.replace(target_export_state.strip(), replacement_export_state.strip())

# 2. handleExportExecute
target_export_exec = """
  const handleExportExecute = async () => {
    setLoading(true);
    try {
      if (isMobile()) {
        // Single ZIP (part1 + part2 + formula) — one download, works on iOS Safari.
        downloadViaUrl(`${API_BASE}/api/export_zip?interval=${interval}`);
      } else {
        await downloadFile(`${API_BASE}/api/export?interval=${interval}&part=1`, `ztrade_export_${interval}_part1.csv`);
        await downloadFile(`${API_BASE}/api/export?interval=${interval}&part=2`, `ztrade_export_${interval}_part2.csv`);
      }
    } catch (err) {
"""
replacement_export_exec = """
  const handleExportExecute = async () => {
    setLoading(true);
    try {
      const listParam = selectedWatchlist !== 'All Symbols' ? `&list_name=${encodeURIComponent(selectedWatchlist)}` : '';
      if (isMobile()) {
        // Single ZIP (part1 + part2 + formula) — one download, works on iOS Safari.
        downloadViaUrl(`${API_BASE}/api/export_zip?interval=${interval}${listParam}`);
      } else {
        await downloadFile(`${API_BASE}/api/export?interval=${interval}&part=1${listParam}`, `ztrade_export_${interval}_part1.csv`);
        await downloadFile(`${API_BASE}/api/export?interval=${interval}&part=2${listParam}`, `ztrade_export_${interval}_part2.csv`);
      }
    } catch (err) {
"""
content = content.replace(target_export_exec.strip(), replacement_export_exec.strip())

# 3. handleExport
target_handle_export = """
  const handleExport = () => {
    showConfirm({
      title: 'ยืนยัน Download History',
      message: `ต้องการดาวน์โหลดข้อมูล Interval "${interval}" (2 ไฟล์) ใช่หรือไม่?`,
      confirmText: 'ดาวน์โหลด',
      type: 'info',
      onConfirm: handleExportExecute,
    });
  };
"""
replacement_handle_export = """
  const handleExport = async () => {
    setLoading(true);
    try {
      const res = await axios.get(`${API_BASE}/api/export/check?interval=${interval}&list_name=${encodeURIComponent(selectedWatchlist)}`);
      const { available_count, missing_count, total_in_list } = res.data;
      
      let msg = `ต้องการดาวน์โหลดข้อมูล Interval "${interval}" ใช่หรือไม่?\\n\\n`;
      if (selectedWatchlist === 'All Symbols') {
         msg += `พบข้อมูลที่มีประวัติทั้งหมด ${available_count} ตัว`;
      } else {
         msg += `Watchlist "${selectedWatchlist}" มีหุ้นทั้งหมด ${total_in_list} ตัว\\n`;
         msg += `- มีประวัติพร้อม Export: ${available_count} ตัว\\n`;
         if (missing_count > 0) {
            msg += `- ไม่มีประวัติ: ${missing_count} ตัว (จะไม่ถูก Export)\\n`;
         }
      }
      
      showConfirm({
        title: 'ยืนยัน Download History',
        message: msg,
        confirmText: 'ดาวน์โหลด',
        type: 'info',
        onConfirm: handleExportExecute,
      });
    } catch (err) {
      console.error(err);
      alert('ไม่สามารถตรวจสอบข้อมูลประวัติได้');
    } finally {
      setLoading(false);
    }
  };
"""
content = content.replace(target_handle_export.strip(), replacement_handle_export.strip())

# 4. ExportView UI
target_export_ui = """
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-8 space-y-8 max-w-4xl mx-auto">
        <div className="flex flex-col md:flex-row gap-6">
"""
replacement_export_ui = """
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-8 space-y-8 max-w-4xl mx-auto">
        {/* Watchlist Selection */}
        <div className="flex flex-col sm:flex-row items-center gap-4 border-b border-gray-100 pb-6">
          <span className="text-gray-700 font-semibold min-w-[120px]">เลือก Watchlist:</span>
          <div className="relative w-full sm:w-64">
            <select
              value={selectedWatchlist}
              onChange={(e) => setSelectedWatchlist(e.target.value)}
              className="w-full appearance-none bg-gray-50 border border-gray-200 text-gray-700 py-2.5 pl-4 pr-10 rounded-xl leading-tight focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent font-medium"
            >
              <option value="All Symbols">All Symbols</option>
              {Object.keys(watchlists).map((name) => (
                <option key={name} value={name}>{name}</option>
              ))}
            </select>
            <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-4 text-gray-500">
              <ChevronDown className="w-4 h-4" />
            </div>
          </div>
        </div>

        <div className="flex flex-col md:flex-row gap-6">
"""
content = content.replace(target_export_ui.strip(), replacement_export_ui.strip())

with open("dash/src/App.tsx", "w") as f:
    f.write(content)
