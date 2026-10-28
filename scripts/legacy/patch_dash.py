import re

with open("dash/src/App.tsx", "r") as f:
    content = f.read()

# 1. Add states to DashboardView
target_state = """
function DashboardView() {
  const [symbol, setSymbol] = useState('BTCUSDT');
"""
replacement_state = """
function DashboardView() {
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

  const [symbol, setSymbol] = useState('BTCUSDT');
"""
content = content.replace(target_state.strip(), replacement_state.strip())

# 2. Modify startAutomateExecute
target_start = """
  const startAutomateExecute = () => startCustomRun(SYMBOLS, interval, extendedSession);
"""
replacement_start = """
  const startAutomateExecute = () => {
    let targets = SYMBOLS;
    if (selectedWatchlist !== 'All Symbols' && watchlists[selectedWatchlist]) {
      const symbolsInList = watchlists[selectedWatchlist].map(s => s.symbol);
      targets = SYMBOLS.filter(s => symbolsInList.includes(s.symbol));
    }
    startCustomRun(targets, interval, extendedSession);
  };
"""
content = content.replace(target_start.strip(), replacement_start.strip())

# 3. Update confirmation message
target_confirm = """
    showConfirm({
      title: 'เริ่มระบบ Automate All',
      message: `คุณต้องการดึงข้อมูลสำหรับทุก Symbol (${SYMBOLS.length} ตัว) ตามการตั้งค่าตัวกรองปัจจุบันใช่หรือไม่?`,
"""
replacement_confirm = """
    showConfirm({
      title: 'เริ่มระบบ Automate All',
      message: `คุณต้องการดึงข้อมูลสำหรับ ${selectedWatchlist !== 'All Symbols' ? `Watchlist: ${selectedWatchlist}` : 'ทุก Symbol'} ตามการตั้งค่าตัวกรองปัจจุบันใช่หรือไม่?`,
"""
content = content.replace(target_confirm.strip(), replacement_confirm.strip())

# 4. Add UI selector for Watchlist
target_ui = """
      {/* Automate Section */}
      <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 mb-8 animate-in fade-in slide-in-from-bottom-2 duration-500 delay-150 relative">
        <h3 className="text-sm font-bold text-gray-500 mb-4 uppercase tracking-wider">ดึงข้อมูลอัตโนมัติ (Automate)</h3>
        <div className="flex flex-col sm:flex-row gap-4 items-center">
"""
replacement_ui = """
      {/* Automate Section */}
      <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 mb-8 animate-in fade-in slide-in-from-bottom-2 duration-500 delay-150 relative">
        <h3 className="text-sm font-bold text-gray-500 mb-4 uppercase tracking-wider">ดึงข้อมูลอัตโนมัติ (Automate)</h3>
        <div className="flex flex-col sm:flex-row gap-4 items-center">
          <div className="flex-1 w-full sm:w-auto relative">
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
"""
content = content.replace(target_ui.strip(), replacement_ui.strip())

with open("dash/src/App.tsx", "w") as f:
    f.write(content)
