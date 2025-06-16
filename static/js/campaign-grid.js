function render_grid(gridContainer, nrows, ncols, campaign_id) {
    gridContainer.innerHTML = '';
    const relative_button_width = 800/ncols
    const relative_button_height = 900/nrows
    gridContainer.style.gridTemplateColumns = `repeat(${ncols}, ${relative_button_width}px)`;
    gridContainer.style.gridTemplateRows = `repeat(${nrows}, ${relative_button_height}px)`;
    let row = 0;
    let col = 0;
    const minFontSize = 10;
    const maxFontSize = 24;
    let fontSize = Math.min(relative_button_width, relative_button_height) / 5;
    fontSize = Math.max(minFontSize, Math.min(maxFontSize, fontSize));
    for (let i = 0; i < nrows * ncols; i++) {
        const cellButton = document.createElement('text');

        cellButton.disabled = true;
        cellButton.innerText = `${(nrows-1-row)*ncols + col}`;
        cellButton.classList.add('grid-button');
        cellButton.style.fontSize = fontSize + 'px';
        cellButton.style.width = `${relative_button_width}px`;
        cellButton.style.height = `${relative_button_height}px`;
        cellButton.setAttribute('cellid', `${(nrows-1-row)*ncols + col}`);
        cellButton.setAttribute('colors', `None`);


        const tooltip = document.createElement('span');
        tooltip.innerText = '';
        tooltip.style.visibility = 'hidden';  // Hide the tooltip by default
        tooltip.style.position = 'relative';
        tooltip.style.bottom = '100%';  // Position above the button
        // {#tooltip.style.left = '50%';#}
        // {#tooltip.style.transform = 'translateX(-50%)';#}
        // {#tooltip.style.backgroundColor = '#555';  // Tooltip background color#}
        // {#tooltip.style.opacity = '0';  // Make the tooltip fade in#}
        // {#tooltip.style.textAlign = 'left';#}


        tooltip.style.color = 'blue';

        tooltip.style.borderRadius = '5px';
        tooltip.style.padding = '5px';
        tooltip.style.width = '100%';
        tooltip.style.setProperty('white-space', 'nowrap');

        tooltip.style.transition = 'opacity 0.3s ease';  // Smooth fade transition
        cellButton.addEventListener('click', () => {
            const cellid = cellButton.getAttribute('cellid')
            const colors = cellButton.getAttribute('colors')
            if (cellid !== undefined) {
                $.ajax({
                    url: campaign_id + "/" + cellid,
                    dataType: "json",
                    type: "GET",
                    success: function (data) {
                        file_id = data[0].file_id
                        window.open('http://localhost:8000/files/' + file_id, '_blank').focus();
                    }
                });
            }
        });

        // Append the tooltip to the button
        // cellButton.appendChild(tooltip);
        //   cellButton.addEventListener('mouseover', () => {
        //   console.log(cellButton.getAttribute('cellid') + ": color: " + cellButton.getAttribute('colors'))
        // });
        //
        // cellButton.addEventListener('mouseenter', () => {
        //  tooltip.style.visibility = 'visible';  // Show the tooltip
        //  tooltip.style.opacity = '1';  // Fade in
        // });
        //
        // cellButton.addEventListener('mouseleave', () => {
        //   tooltip.style.visibility = 'hidden';
        //   tooltip.style.opacity = '0'; // Hide the tooltip with opacity
        // });

        gridContainer.appendChild(cellButton);
        if(col == (ncols-1)) {
            col = 0
            row = row+1
        } else {
            col = col+1
        }
    }
}


function color_cell(cell_id, color) {
    cell = document.querySelectorAll(`[cellid='${cell_id}']`)[0];
    cell.style.background = '#9ACD32'
    cell.setAttribute('colors', cell.style.background);
    // cell.getElementsByTagName('span')[0].innerText = cell.style.background
}