// Small bits of JavaScript for CloSet50

// 1. Upload form: only show the "Style" choices that match the chosen clothing type
const category = document.querySelector("#category");
const subtype = document.querySelector("#subtype");
const subtypeLabel = document.querySelector("#subtype-label");

function updateSubtypes() {
    let count = 0;
    for (const option of subtype.querySelectorAll("option[data-category]")) {
        const show = option.dataset.category === category.value;
        option.hidden = !show;
        if (show) count++;
        if (!show && option.selected) subtype.value = "";
    }
    // Dresses and shoes have no styles, so hide the whole dropdown
    subtypeLabel.hidden = count === 0;
    subtype.required = count > 0;
}

if (category && subtype) {
    category.addEventListener("change", updateSubtypes);
    updateSubtypes();
}

// 2. Upload form: show a preview of the chosen photo
const photo = document.querySelector("#photo");
const preview = document.querySelector("#preview");
if (photo && preview) {
    photo.addEventListener("change", () => {
        if (photo.files[0]) {
            preview.src = URL.createObjectURL(photo.files[0]);
            preview.hidden = false;
        }
    });
}

// 3. Outfit builder: show the picked items side by side at the top
const board = document.querySelector("#board");
if (board) {
    const boxes = document.querySelectorAll(".pick input");

    function updateBoard() {
        board.innerHTML = "";
        for (const box of boxes) {
            if (box.checked) {
                const figure = document.createElement("figure");
                const img = document.createElement("img");
                img.src = box.dataset.image;
                const caption = document.createElement("figcaption");
                caption.textContent = box.dataset.name;
                figure.append(img, caption);
                board.append(figure);
            }
        }
        if (board.children.length === 0) {
            board.innerHTML = '<p class="small">Nothing picked yet.</p>';
        }
    }

    boxes.forEach(box => box.addEventListener("change", updateBoard));
    updateBoard();
}
