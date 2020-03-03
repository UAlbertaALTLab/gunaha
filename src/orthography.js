/**
 * Orthography switching.
 */

const AVAILABLE_ORTHOGRAPHIES = new Set(['Cans', 'Latn', 'LatnXMacron'])

/**
 * Listen to ALL clicks on the page, and change orthography for elements that
 * have the data-orth-switch.
 */
export function registerEventListener() {
  // Try to handle a click on ANYTHING.
  // This way, if new elements appear on the page dynamically, we never
  // need to register new event listeners: this one will work for all of them.
  document.body.addEventListener('click', handleClickSwitchOrthography)
}

/**
 * Changes the orthography of EVERYTHING on the page.
 */
export function changeOrth (which) {
  if (!AVAILABLE_ORTHOGRAPHIES.has(which)) {
    throw new Error(`tried to switch to unknown orthography: ${which}`)
  }

  let elements = document.querySelectorAll('[data-orth]')
  let attr = `orth${which}`
  for (let el of elements) {
    let newText = el.dataset[attr]
    if (newText) {
      el.innerText = newText
    }
  }
}

/**
 * Switches orthography. This assumes the following HTML:
 *
 *  <details>
 *    <summary>CURRENT ORTHOGRAPHY</summary>
 *    <ul>
 *      <li class="menu-choice menu-choice--selected">
 *        <button data-orth-switch value="ORTH">CURRENT ORTHOGRAPHY</button>
 *      </li>
 *      <li class="menu-choice">
 *        <button data-orth-switch value="ORTH">DIFFERENT ORTHOGRAPHY</button>
 *      </li>
 *    </ul>
 *  </details>
 */
function handleClickSwitchOrthography(evt) {
  let target = evt.target
  // Determine that this is a orthography changing button.
  if (target.dataset.orthSwitch === undefined) {
    return
  }

  // target is a <button data-orth-swith value="ORTHOGRAPHY">
  let orth = target.value
  changeOrth(orth)

  ////////////////////// Update the UI appropriately /////////////////////////

  // Climb up the DOM tree to find the <details> and its <summary> that contains the title.
  let detailsElement = target.closest('details')
  if (!detailsElement) {
    // there absolutely should be a <de
    throw new Error('Could not find relevant <details> element!')
  }
  let summaryElement = detailsElement.querySelector('summary')
  if (!summaryElement) {
    throw new Error('Could not find relevant <summary> element!')
  }

  // Change the title appropriately and close the menu
  summaryElement.innerText = target.innerText
  detailsElement.open = false

  // Clear the selected class from all options
  for (let el of detailsElement.querySelectorAll('[data-orth-switch]')) {
    let li = el.closest('.menu-choice')
    li.classList.remove('menu-choice--selected')
  }
  target.closest('.menu-choice').classList.add('menu-choice--selected')
}
