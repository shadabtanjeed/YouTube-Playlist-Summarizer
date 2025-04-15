document.addEventListener('DOMContentLoaded', function () {
    // State variables
    let currentStep = 1;
    let contentType = 'video'; // Default to video
    let youtubeLink = '';
    let summaryStyle = 'detailed';
    let summaryData = null;

    // Elements
    const steps = document.querySelectorAll('.step');
    const styleOptions = document.querySelectorAll('.style-option');
    const youtubeLinkInput = document.getElementById('youtube-link');
    const linkErrorElement = document.getElementById('link-error');
    const tabs = document.querySelectorAll('.tab');
    const tabContents = document.querySelectorAll('.tab-content');

    // Content Type Selection
    document.querySelectorAll('.content-option').forEach(option => {
        option.addEventListener('click', function () {
            document.querySelectorAll('.content-option').forEach(opt => opt.classList.remove('selected'));
            this.classList.add('selected');
            contentType = this.dataset.type;
            console.log('Content type selected:', contentType);
        });
    });

    // Style Selection
    styleOptions.forEach(option => {
        option.addEventListener('click', function () {
            styleOptions.forEach(opt => opt.classList.remove('selected'));
            this.classList.add('selected');
            summaryStyle = this.dataset.style;
            console.log('Style selected:', summaryStyle);
        });
    });

    // Submit button
    document.getElementById('submit-request').addEventListener('click', function () {
        console.log('Submit button clicked');

        // Check if YouTube link is provided
        youtubeLink = youtubeLinkInput.value.trim();

        if (!youtubeLink) {
            linkErrorElement.textContent = 'Please enter a YouTube link';
            return;
        }

        if (!isValidYouTubeUrl(youtubeLink)) {
            linkErrorElement.textContent = 'Please enter a valid YouTube link';
            return;
        }

        linkErrorElement.textContent = '';
        console.log('Form validated successfully');
        console.log('Content type:', contentType);
        console.log('YouTube link:', youtubeLink);
        console.log('Style:', summaryStyle);

        // Show loading state
        document.getElementById('single-form-panel').classList.remove('active');
        document.getElementById('loading-step').classList.add('active');

        if (contentType === 'video') {
            fetchVideoSummary(youtubeLink, summaryStyle);
        } else if (contentType === 'playlist') {
            fetchPlaylistSummary(youtubeLink, summaryStyle);
        }
    });

    // Tab functionality
    tabs.forEach(tab => {
        tab.addEventListener('click', function () {
            const tabId = this.dataset.tab;

            tabs.forEach(t => t.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));

            this.classList.add('active');
            document.getElementById(tabId).classList.add('active');
        });
    });

    // Result actions
    if (document.getElementById('copy-summary')) {
        document.getElementById('copy-summary').addEventListener('click', function () {
            const summaryContent = document.getElementById('summary-content').innerText;
            copyToClipboard(summaryContent);
            showToast('Summary copied to clipboard!');
        });
    }

    if (document.getElementById('download-summary')) {
        document.getElementById('download-summary').addEventListener('click', function () {
            downloadSummary();
        });
    }

    if (document.getElementById('new-summary')) {
        document.getElementById('new-summary').addEventListener('click', function () {
            resetForm();
        });
    }

    // Helper Functions
    function isValidYouTubeUrl(url) {
        // Basic validation for YouTube URLs or video IDs
        return url.includes('youtube.com') || url.includes('youtu.be') ||
            /^[A-Za-z0-9_-]{11}$/.test(url);
    }

    function fetchVideoSummary(videoUrl, style) {
        const requestData = {
            video_url: videoUrl,
            style: style,
            save_to_file: true
        };

        console.log('Sending video summary request:', requestData);

        fetch('/api/summarize/video/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify(requestData)
        })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                console.log('Summary data received:', data);
                summaryData = data;
                displayResults(data);
                document.getElementById('loading-step').classList.remove('active');
                document.getElementById('result-step').classList.add('active');
            })
            .catch(error => {
                console.error('Error:', error);
                document.getElementById('loading-message').textContent = 'Error: ' + error.message;
                setTimeout(() => {
                    document.getElementById('loading-step').classList.remove('active');
                    document.getElementById('single-form-panel').classList.add('active');
                }, 3000);
            });
    }

    function fetchPlaylistSummary(playlistUrl, style) {
        document.getElementById('loading-message').textContent = 'Processing playlist... This may take several minutes.';

        const requestData = {
            playlist_url: playlistUrl,
            style: style,
            save_to_file: true
        };

        console.log('Sending playlist summary request:', requestData);

        fetch('/api/summarize/playlist/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify(requestData)
        })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                console.log('Playlist data received:', data);
                summaryData = data;
                displayPlaylistResults(data);
                document.getElementById('loading-step').classList.remove('active');
                document.getElementById('result-step').classList.add('active');
            })
            .catch(error => {
                console.error('Error:', error);
                document.getElementById('loading-message').textContent = 'Error: ' + error.message;
                setTimeout(() => {
                    document.getElementById('loading-step').classList.remove('active');
                    document.getElementById('single-form-panel').classList.add('active');
                }, 3000);
            });
    }

    function displayResults(data) {
        // Display summary
        const summaryContent = document.getElementById('summary-content');
        summaryContent.innerHTML = formatContent(data.summary);

        // Display transcript if available
        const transcriptContent = document.getElementById('transcript-content');
        if (data.transcript) {
            transcriptContent.innerHTML = formatContent(data.transcript);
        } else {
            transcriptContent.innerHTML = '<p class="text-muted">No transcript available.</p>';
        }

        // Hide playlist tab for single videos
        document.getElementById('playlist-tab-container').style.display = 'none';
    }

    function displayPlaylistResults(data) {
        // Get the playlist summary data
        const playlistInfo = data.playlist_info;
        const summaries = data.summaries;

        // Show the playlist tab
        document.getElementById('playlist-tab-container').style.display = 'block';

        // Display combined summary in summary tab
        const summaryContent = document.getElementById('summary-content');
        summaryContent.innerHTML = `<h3>Playlist: ${playlistInfo.url}</h3>
                                   <p>Total videos: ${playlistInfo.video_count}</p>
                                   <p>Summary style: ${playlistInfo.style}</p>
                                   <p>See individual video summaries in the "All Videos" tab.</p>`;

        // No transcript for playlists
        const transcriptContent = document.getElementById('transcript-content');
        transcriptContent.innerHTML = '<p class="text-muted">Transcript view is not available for playlists.</p>';

        // Display individual video summaries in the playlist tab
        const playlistContent = document.getElementById('playlist-content');
        playlistContent.innerHTML = '';

        // Add an option to load and fetch all summaries if needed
        const fetchAllSummariesButton = document.createElement('button');
        fetchAllSummariesButton.className = 'btn btn-primary fetch-all-summaries';
        fetchAllSummariesButton.textContent = 'Load All Summaries';
        fetchAllSummariesButton.style.marginBottom = '1rem';
        playlistContent.appendChild(fetchAllSummariesButton);
        
        fetchAllSummariesButton.addEventListener('click', function() {
            this.textContent = 'Loading...';
            this.disabled = true;
            fetchAllVideoSummaries(summaries);
        });

        summaries.forEach((video, index) => {
            const videoElement = document.createElement('div');
            videoElement.className = `playlist-video-item ${video.success ? 'success' : 'error'}`;
            videoElement.setAttribute('data-video-id', video.video_id);

            let videoHtml = `
                <h3>${index + 1}. ${video.title}</h3>
                <p>Video ID: ${video.video_id}</p>
            `;

            if (video.success) {
                // Check if we have the actual summary content
                if (video.summary) {
                    // We already have the summary content
                    const summaryPreview = video.summary.substring(0, 100) + '...';
                    videoHtml += `
                        <div class="summary-preview">
                            <p>${summaryPreview}</p>
                            <button class="btn btn-secondary view-full-summary">View Full Summary</button>
                        </div>
                        <div class="full-summary" style="display: none;">
                            <p>${formatContent(video.summary)}</p>
                            <button class="btn btn-secondary hide-full-summary">Collapse</button>
                        </div>
                    `;
                } else if (video.file_path) {
                    // We have a file path but need to fetch content
                    videoHtml += `
                        <p class="summary-status">Summary available</p>
                        <button class="btn btn-secondary load-summary" data-video-id="${video.video_id}">Load Summary</button>
                    `;
                } else {
                    videoHtml += `<p class="summary-status">Summary information incomplete</p>`;
                }
            } else {
                videoHtml += `<p class="error-message">Error: ${video.error || 'Unknown error'}</p>`;
            }

            videoElement.innerHTML = videoHtml;
            playlistContent.appendChild(videoElement);
            
            // Add event listeners for summary expansion buttons
            const viewFullBtn = videoElement.querySelector('.view-full-summary');
            const hideFullBtn = videoElement.querySelector('.hide-full-summary');
            const loadSummaryBtn = videoElement.querySelector('.load-summary');
            
            if (viewFullBtn) {
                viewFullBtn.addEventListener('click', function() {
                    const summaryPreview = this.parentNode;
                    const fullSummary = summaryPreview.nextElementSibling;
                    
                    summaryPreview.style.display = 'none';
                    fullSummary.style.display = 'block';
                });
            }
            
            if (hideFullBtn) {
                hideFullBtn.addEventListener('click', function() {
                    const fullSummary = this.parentNode;
                    const summaryPreview = fullSummary.previousElementSibling;
                    
                    fullSummary.style.display = 'none';
                    summaryPreview.style.display = 'block';
                });
            }
            
            if (loadSummaryBtn) {
                loadSummaryBtn.addEventListener('click', function() {
                    const videoId = this.getAttribute('data-video-id');
                    const statusElement = this.previousElementSibling;
                    const buttonElement = this;
                    
                    // Change status while loading
                    statusElement.textContent = 'Loading summary...';
                    buttonElement.disabled = true;
                    
                    // Fetch the individual video summary
                    fetchVideoSummaryContent(videoId, playlistInfo.style)
                        .then(summaryContent => {
                            // Replace the entire content of the video item
                            const videoContainer = buttonElement.closest('.playlist-video-item');
                            const title = videoContainer.querySelector('h3').textContent;
                            const idText = videoContainer.querySelector('p').textContent;
                            
                            const summaryPreview = summaryContent.substring(0, 100) + '...';
                            videoContainer.innerHTML = `
                                <h3>${title}</h3>
                                <p>${idText}</p>
                                <div class="summary-preview">
                                    <p>${summaryPreview}</p>
                                    <button class="btn btn-secondary view-full-summary">View Full Summary</button>
                                </div>
                                <div class="full-summary" style="display: none;">
                                    <p>${formatContent(summaryContent)}</p>
                                    <button class="btn btn-secondary hide-full-summary">Collapse</button>
                                </div>
                            `;
                            
                            // Re-attach event listeners
                            const newViewBtn = videoContainer.querySelector('.view-full-summary');
                            const newHideBtn = videoContainer.querySelector('.hide-full-summary');
                            
                            newViewBtn.addEventListener('click', function() {
                                const preview = this.parentNode;
                                const full = preview.nextElementSibling;
                                preview.style.display = 'none';
                                full.style.display = 'block';
                            });
                            
                            newHideBtn.addEventListener('click', function() {
                                const full = this.parentNode;
                                const preview = full.previousElementSibling;
                                full.style.display = 'none';
                                preview.style.display = 'block';
                            });
                        })
                        .catch(error => {
                            statusElement.textContent = 'Error loading summary: ' + error.message;
                            buttonElement.disabled = false;
                        });
                });
            }
        });
    }
    
    // Function to fetch summary content from a file
    async function fetchVideoSummaryContent(videoId, style) {
        try {
            // Create a unique request ID to avoid caching issues
            const requestId = Date.now();
            
            // Fetch the summary content from the API
            const response = await fetch(`/api/summarize/video/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({
                    video_id: videoId,
                    style: style || 'detailed'
                })
            });
            
            if (!response.ok) {
                throw new Error(`Failed to fetch summary (status ${response.status})`);
            }
            
            const data = await response.json();
            
            if (data.error) {
                throw new Error(data.error);
            }
            
            return data.summary || 'No summary content available.';
        } catch (error) {
            console.error('Error fetching summary content:', error);
            throw error;
        }
    }
    
    // Function to fetch all summaries for a playlist
    async function fetchAllVideoSummaries(videos) {
        const playlistContent = document.getElementById('playlist-content');
        const fetchAllButton = playlistContent.querySelector('.fetch-all-summaries');
        
        try {
            // Process videos sequentially to avoid overwhelming the API
            for (const video of videos) {
                if (!video.success || video.summary) continue; // Skip errors or already loaded summaries
                
                const videoElement = playlistContent.querySelector(`.playlist-video-item[data-video-id="${video.video_id}"]`);
                if (!videoElement) continue;
                
                const statusElement = videoElement.querySelector('.summary-status');
                const loadButton = videoElement.querySelector('.load-summary');
                
                if (statusElement) statusElement.textContent = 'Loading summary...';
                if (loadButton) loadButton.disabled = true;
                
                try {
                    const summaryContent = await fetchVideoSummaryContent(video.video_id, video.style);
                    
                    // Update the video element with the fetched summary
                    const title = videoElement.querySelector('h3').textContent;
                    const idText = videoElement.querySelector('p').textContent;
                    
                    const summaryPreview = summaryContent.substring(0, 100) + '...';
                    videoElement.innerHTML = `
                        <h3>${title}</h3>
                        <p>${idText}</p>
                        <div class="summary-preview">
                            <p>${summaryPreview}</p>
                            <button class="btn btn-secondary view-full-summary">View Full Summary</button>
                        </div>
                        <div class="full-summary" style="display: none;">
                            <p>${formatContent(summaryContent)}</p>
                            <button class="btn btn-secondary hide-full-summary">Collapse</button>
                        </div>
                    `;
                    
                    // Re-attach event listeners
                    const newViewBtn = videoElement.querySelector('.view-full-summary');
                    const newHideBtn = videoElement.querySelector('.hide-full-summary');
                    
                    newViewBtn.addEventListener('click', function() {
                        const preview = this.parentNode;
                        const full = preview.nextElementSibling;
                        preview.style.display = 'none';
                        full.style.display = 'block';
                    });
                    
                    newHideBtn.addEventListener('click', function() {
                        const full = this.parentNode;
                        const preview = full.previousElementSibling;
                        full.style.display = 'none';
                        preview.style.display = 'block';
                    });
                    
                } catch (error) {
                    if (statusElement) statusElement.textContent = 'Error loading summary: ' + error.message;
                    if (loadButton) loadButton.disabled = false;
                }
                
                // Add a small delay between requests to avoid overwhelming the API
                await new Promise(resolve => setTimeout(resolve, 500));
            }
            
            // Update the fetch all button
            if (fetchAllButton) {
                fetchAllButton.textContent = 'All Summaries Loaded';
                fetchAllButton.disabled = true;
            }
            
        } catch (error) {
            console.error('Error fetching all summaries:', error);
            if (fetchAllButton) {
                fetchAllButton.textContent = 'Error Loading Summaries';
                fetchAllButton.disabled = false;
            }
        }
    }

    function formatContent(content) {
        if (!content) return '<p class="text-muted">No content available.</p>';

        // Replace line breaks with HTML breaks
        return content.replace(/\n/g, '<br>');
    }

    function copyToClipboard(text) {
        const textarea = document.createElement('textarea');
        textarea.value = text;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
    }

    function downloadSummary() {
        if (!summaryData) return;

        let filename, content;

        if (contentType === 'video') {
            filename = `summary_${extractVideoId(youtubeLink)}_${summaryStyle}.txt`;
            content = `Summary for: ${youtubeLink}\n\n`;

            if (summaryData.transcript) {
                content += `TRANSCRIPT:\n\n${summaryData.transcript}\n\n`;
            }

            content += `SUMMARY:\n\n${summaryData.summary}`;
        } else {
            const playlistId = youtubeLink.includes('list=') ?
                youtubeLink.split('list=')[1].split('&')[0] : 'playlist';

            filename = `playlist_${playlistId}_summary.txt`;
            content = `Summaries for playlist: ${youtubeLink}\n`;
            content += `Total videos: ${summaryData.playlist_info.video_count}\n\n`;

            summaryData.summaries.forEach((video, index) => {
                content += `Video ${index + 1}: ${video.title}\n`;
                content += `URL: ${video.video_url || 'N/A'}\n`;

                if (video.success) {
                    content += `Summary available in: ${video.file_path || 'N/A'}\n`;
                } else {
                    content += `Error: ${video.error || 'Unknown error'}\n`;
                }

                content += `\n${'='.repeat(50)}\n\n`;
            });
        }

        const blob = new Blob([content], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);

        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    function extractVideoId(url) {
        if (url.includes('v=')) {
            return url.split('v=')[1].split('&')[0];
        } else if (url.includes('youtu.be/')) {
            return url.split('youtu.be/')[1].split('?')[0];
        }

        // Assume the URL is just an ID
        return url;
    }

    function resetForm() {
        // Reset form and show it again
        document.getElementById('youtube-link').value = '';
        document.getElementById('link-error').textContent = '';

        // Hide results and show form
        document.getElementById('result-step').classList.remove('active');
        document.getElementById('single-form-panel').classList.add('active');

        // Reset tabs
        tabs[0].click();
    }

    function showToast(message) {
        // Create toast element
        const toast = document.createElement('div');
        toast.className = 'toast';
        toast.textContent = message;
        document.body.appendChild(toast);

        // Show and then hide after delay
        setTimeout(() => {
            toast.classList.add('show');
        }, 100);

        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => {
                document.body.removeChild(toast);
            }, 300);
        }, 3000);
    }

    // Get CSRF token for secure POST requests
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    // Add toast styling if not already present
    if (!document.querySelector('style#toast-style')) {
        const style = document.createElement('style');
        style.id = 'toast-style';
        style.textContent = `
            .toast {
                position: fixed;
                bottom: 20px;
                left: 50%;
                transform: translateX(-50%) translateY(100px);
                background-color: #333;
                color: white;
                padding: 12px 24px;
                border-radius: 4px;
                opacity: 0;
                transition: all 0.3s ease;
                z-index: 1000;
            }
            
            .toast.show {
                opacity: 1;
                transform: translateX(-50%) translateY(0);
            }
        `;
        document.head.appendChild(style);
    }

    console.log('YouTube Summarizer script initialized');
});