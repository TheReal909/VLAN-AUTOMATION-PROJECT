(() => {
  const picker = document.querySelector("[data-facility-picker]");
  if (!picker) return;

  const input = picker.querySelector('[role="combobox"]');
  const select = picker.querySelector(".facility-native-select");
  const listbox = picker.querySelector('[role="listbox"]');
  const options = Array.from(select.options).filter((option) => option.value);
  let activeIndex = -1;
  let visibleOptions = [];

  const closeList = () => {
    listbox.hidden = true;
    input.setAttribute("aria-expanded", "false");
    input.removeAttribute("aria-activedescendant");
    activeIndex = -1;
  };

  const setActive = (index) => {
    activeIndex = index;
    visibleOptions.forEach((option, optionIndex) => {
      const row = listbox.children[optionIndex];
      row.classList.toggle("active", optionIndex === activeIndex);
      row.setAttribute(
        "aria-selected",
        optionIndex === activeIndex ? "true" : "false",
      );
    });
    const active = listbox.children[activeIndex];
    if (active) {
      input.setAttribute("aria-activedescendant", active.id);
      active.scrollIntoView({ block: "nearest" });
    } else {
      input.removeAttribute("aria-activedescendant");
    }
  };

  const choose = (option) => {
    select.value = option.value;
    input.value = option.textContent.trim();
    closeList();
    input.setCustomValidity("");
  };

  const renderOptions = () => {
    const query = input.value.trim().toLocaleLowerCase();
    visibleOptions = options.filter((option) =>
      option.textContent.toLocaleLowerCase().includes(query),
    );
    listbox.replaceChildren();

    if (!visibleOptions.length) {
      const empty = document.createElement("div");
      empty.className = "facility-empty";
      empty.textContent = "No matching facilities";
      empty.setAttribute("role", "option");
      empty.setAttribute("aria-disabled", "true");
      listbox.append(empty);
    } else {
      visibleOptions.forEach((option, index) => {
        const row = document.createElement("div");
        row.id = `facility-option-${index}`;
        row.className = "facility-option";
        row.setAttribute("role", "option");
        row.setAttribute("aria-selected", "false");
        row.textContent = option.textContent.trim();
        row.addEventListener("mousedown", (event) => event.preventDefault());
        row.addEventListener("click", () => choose(option));
        listbox.append(row);
      });
    }

    listbox.hidden = false;
    input.setAttribute("aria-expanded", "true");
    setActive(-1);
  };

  const selected = select.options[select.selectedIndex];
  if (selected && selected.value) input.value = selected.textContent.trim();

  input.addEventListener("focus", renderOptions);
  input.addEventListener("input", () => {
    select.value = "";
    input.setCustomValidity("");
    renderOptions();
  });
  input.addEventListener("keydown", (event) => {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      if (listbox.hidden) renderOptions();
      if (visibleOptions.length)
        setActive(Math.min(activeIndex + 1, visibleOptions.length - 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      if (visibleOptions.length) setActive(Math.max(activeIndex - 1, 0));
    } else if (event.key === "Enter" && !listbox.hidden && activeIndex >= 0) {
      event.preventDefault();
      choose(visibleOptions[activeIndex]);
    } else if (event.key === "Escape") {
      closeList();
    }
  });
  input.addEventListener("blur", closeList);
  input.form.addEventListener("submit", (event) => {
    if (!select.value) {
      event.preventDefault();
      input.setCustomValidity("Choose a facility from the suggestions.");
      input.reportValidity();
    }
  });
})();
