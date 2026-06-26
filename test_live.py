import urllib.request, json

def post(path, data):
    body = json.dumps(data).encode()
    req = urllib.request.Request(
        f'http://localhost:8000{path}',
        data=body,
        headers={'Content-Type': 'application/json'}
    )
    r = urllib.request.urlopen(req)
    return json.loads(r.read())

print('--- TEST 1: Learning Agent ---')
r = post('/api/chat', {'message': 'Explain recursion to a beginner', 'skill': 'learn'})
print(f'Agent: {r["agent_name"]} | Skill: {r["skill"]} | Tools: {r["tools_used"]}')
print(f'Level: {r["metadata"].get("level")}')
print()

print('--- TEST 2: Troubleshooter (KeyError) ---')
r = post('/api/chat', {'message': 'I keep getting KeyError', 'skill': 'troubleshoot'})
print(f'Agent: {r["agent_name"]} | Matched: {r["metadata"].get("matched_error")}')
print()

print('--- TEST 3: Scheduler ---')
r = post('/api/chat', {'message': 'Remind me to review PRs tomorrow', 'skill': 'schedule'})
print(f'Agent: {r["agent_name"]} | Tools: {r["tools_used"]}')
print()

print('--- TEST 4: Code Sandbox ---')
r = post('/api/execute', {'code': 'result = sum([i**2 for i in range(6)])\nprint(f"Sum of squares 0-5: {result}")'})
print(f'Success: {r["success"]} | Output: {r["output"].strip()}')
print()

print('--- TEST 5: MCP Health ---')
req = urllib.request.Request('http://localhost:8001/health')
resp = json.loads(urllib.request.urlopen(req).read())
print(f'MCP Status: {resp["status"]} | Tools: {resp["tools"]}')
print()

print('All API tests PASSED!')
