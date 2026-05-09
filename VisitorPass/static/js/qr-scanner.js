// Alternative QR Scanner using jsQR
class QRScanner {
    constructor(elementId, onSuccess, onError) {
        this.elementId = elementId;
        this.onSuccess = onSuccess;
        this.onError = onError;
        this.video = null;
        this.canvas = null;
        this.context = null;
        this.scanning = false;
    }

    async render() {
        const container = document.getElementById(this.elementId);
        
        // Create video element
        this.video = document.createElement('video');
        this.video.style.width = '100%';
        this.video.style.maxWidth = '500px';
        this.video.setAttribute('playsinline', true);
        
        // Create canvas for processing
        this.canvas = document.createElement('canvas');
        this.context = this.canvas.getContext('2d');
        
        container.appendChild(this.video);
        
        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: 'environment' }
            });
            
            this.video.srcObject = stream;
            this.video.play();
            
            this.video.addEventListener('loadedmetadata', () => {
                this.canvas.width = this.video.videoWidth;
                this.canvas.height = this.video.videoHeight;
                this.scanning = true;
                this.tick();
            });
        } catch (error) {
            this.onError('Camera access denied or not available');
        }
    }

    tick() {
        if (!this.scanning) return;
        
        if (this.video.readyState === this.video.HAVE_ENOUGH_DATA) {
            this.context.drawImage(this.video, 0, 0, this.canvas.width, this.canvas.height);
            const imageData = this.context.getImageData(0, 0, this.canvas.width, this.canvas.height);
            
            // Here you would use jsQR library to decode
            // For now, this is a placeholder
            // const code = jsQR(imageData.data, imageData.width, imageData.height);
            // if (code) {
            //     this.onSuccess(code.data);
            //     return;
            // }
        }
        
        requestAnimationFrame(() => this.tick());
    }

    clear() {
        this.scanning = false;
        if (this.video && this.video.srcObject) {
            this.video.srcObject.getTracks().forEach(track => track.stop());
        }
    }
}