import re

with open("dash/src/App.tsx", "r") as f:
    content = f.read()

# 1. Add stopAnalysis
target_analyze = """
  const analyze = async () => {
"""
replacement_analyze = """
  const stopAnalysis = async () => {
    try {
      await axios.post(`${API_BASE}/api/gold/automate/stop`);
      // It will throw an error in the backend and resolve the polling loop.
    } catch (e) {
      console.error('Failed to stop analysis', e);
    }
  };

  const analyze = async () => {
"""
content = content.replace(target_analyze.strip(), replacement_analyze.strip())

# 2. Add Stop button in UI
target_ui = """
        <button
          onClick={analyze}
          disabled={loading}
          className="w-full flex justify-center items-center space-x-2 py-3.5 px-4 rounded-lg shadow-sm text-sm font-bold text-white bg-gradient-to-r from-amber-500 to-yellow-600 hover:from-amber-600 hover:to-yellow-700 focus:outline-none disabled:opacity-70 disabled:cursor-not-allowed transition-all cursor-pointer"
        >
          {loading ? (
            <><Loader2 className="w-5 h-5 animate-spin" /><span>กำลังดึงข้อมูล + วิเคราะห์ (อาจใช้เวลา ~30 วิ)...</span></>
          ) : (
            <><Sparkles className="w-5 h-5" /><span>วิเคราะห์จุดเข้า Long / Short</span></>
          )}
        </button>
"""
replacement_ui = """
        <div className="flex gap-2 w-full">
          <button
            onClick={analyze}
            disabled={loading}
            className="flex-1 flex justify-center items-center space-x-2 py-3.5 px-4 rounded-lg shadow-sm text-sm font-bold text-white bg-gradient-to-r from-amber-500 to-yellow-600 hover:from-amber-600 hover:to-yellow-700 focus:outline-none disabled:opacity-70 disabled:cursor-not-allowed transition-all cursor-pointer"
          >
            {loading ? (
              <><Loader2 className="w-5 h-5 animate-spin" /><span>กำลังดึงข้อมูล + วิเคราะห์ (อาจใช้เวลา ~30 วิ)...</span></>
            ) : (
              <><Sparkles className="w-5 h-5" /><span>วิเคราะห์จุดเข้า Long / Short</span></>
            )}
          </button>
          {loading && (
            <button
              onClick={stopAnalysis}
              className="flex justify-center items-center px-6 py-3.5 rounded-lg shadow-sm text-sm font-bold text-white bg-red-600 hover:bg-red-700 focus:outline-none transition-all cursor-pointer"
            >
              Stop
            </button>
          )}
        </div>
"""
content = content.replace(target_ui.strip(), replacement_ui.strip())

with open("dash/src/App.tsx", "w") as f:
    f.write(content)
