let localStream;
let peerConnections = {};
const config = { iceServers: [{ urls: 'stun:stun.l.google.com:19302' }] };

async function startCamera(videoEl) {
  localStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
  videoEl.srcObject = localStream;
}

function createPeer(id, socket) {
  const pc = new RTCPeerConnection(config);

  localStream.getTracks().forEach(track => pc.addTrack(track, localStream));

  pc.ontrack = e => {
    const video = document.createElement('video');
    video.srcObject = e.streams[0];
    video.autoplay = true;
    document.getElementById('videos').appendChild(video);
  };

  return pc;
}