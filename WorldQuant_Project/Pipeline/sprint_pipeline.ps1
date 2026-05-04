Write-Host "===================================================" -ForegroundColor Blue
Write-Host "🚀 WorldQuant 特级大师 Alpha 自动化流水线启动" -ForegroundColor Blue
Write-Host "===================================================" -ForegroundColor Blue

# 第一阶段：AI 因子生成
Write-Host "`n▶️ 第一阶段：启动 AI 剧本挖掘机 (05_AI_Grandmaster_Miner.py)" -ForegroundColor Yellow
Write-Host "正在连接 Gemini 与 WQB 云端去重库..."
python 05_AI_Grandmaster_Miner.py

if ($LASTEXITCODE -ne 0) { 
    Write-Host "`n❌ 矿机运行出错或被手动中断，流水线停止。" -ForegroundColor Red
    exit $LASTEXITCODE 
}

# 第二阶段：多线程回测
Write-Host "`n▶️ 第二阶段：启动终极多线程回测 (10_AI_Alpha_Backtest.py)" -ForegroundColor Yellow
Write-Host "正在读取 ai_crafted_alphas_v2.csv 发送至 WQB 集群..."

# 进入 Candidates 目录执行回测
Push-Location Candidates
python 10_AI_Alpha_Backtest.py
Pop-Location

if ($LASTEXITCODE -ne 0) { 
    Write-Host "`n❌ 回测器运行出错或被手动中断，流水线停止。" -ForegroundColor Red
    exit $LASTEXITCODE 
}

Write-Host "`n===================================================" -ForegroundColor Green
Write-Host "🎉 全自动流水线执行完毕！" -ForegroundColor Green
Write-Host "👉 请打开 Pipeline/Candidates/ra_final_results.csv 提取金牌因子！" -ForegroundColor Green
Write-Host "===================================================" -ForegroundColor Green
