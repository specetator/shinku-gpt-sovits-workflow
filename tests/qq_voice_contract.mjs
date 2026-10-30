// Exercise upstream QQ plugin code with a fake sender; never connects to QQ.
// Node >=22.18. Usage: node tests/qq_voice_contract.mjs <dsh-qqbot checkout> <generated.wav>
import assert from 'node:assert/strict';
import { resolve, dirname } from 'node:path';
import { pathToFileURL } from 'node:url';

const [source, wav] = process.argv.slice(2);
assert(source && wav, 'Provide upstream checkout and generated WAV');
const { registerSendFileTool } = await import(pathToFileURL(resolve(source, 'src/media/send-file-tool.ts')));
let definition;
const calls = [];
const agent = {};
const target = { scope: 'c2c', targetId: 'offline-test-peer' };
let fail = false;
const bot = {
  sendVoice: async (...args) => {
    calls.push(args);
    if (fail) throw new Error('simulated upload failure');
    return { upload: { file_uuid: 'offline-uuid' }, message: { id: 'offline-message' } };
  },
  sendImage: () => assert.fail('WAV must not go to sendImage'),
  sendVideo: () => assert.fail('WAV must not go to sendVideo'),
  sendFile: () => assert.fail('WAV must use sendVoice, not generic file delivery'),
};
registerSendFileTool(
  { get: () => ({ register: value => { definition = value; } }) }, bot,
  { findByAgent: value => value === agent ? { replyTarget: target } : undefined },
  { cwd: resolve('work/non-audio-cwd'), sendFile: { restrictPaths: true, extraRoots: [dirname(resolve(wav))] } },
  { info() {}, warn() {} },
);
const exec = { signal: new AbortController().signal, agent };
const result = await definition.execute({ file_path: resolve(wav) }, exec);
assert.equal(result.messageId, 'offline-message');
assert.equal(calls.length, 1);
assert.deepEqual(calls[0], [target, { localPath: resolve(wav) }]);
await assert.rejects(definition.execute({ file_path: resolve('outside.wav') }, exec), /允许/);
await assert.rejects(definition.execute({ file_path: resolve(wav) }, { signal: exec.signal }), /发送目标/);
fail = true;
await assert.rejects(definition.execute({ file_path: resolve(wav) }, exec), /simulated upload failure/);
console.log('PASS: upstream WAV -> sendVoice, current peer, path allowlist, upload failure');
