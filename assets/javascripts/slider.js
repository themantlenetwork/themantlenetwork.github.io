document.addEventListener("DOMContentLoaded", () => {
  const slider = document.querySelector('.hero-slider');
  if (!slider) return;

  const container = slider.querySelector('.slides');
  const slides = slider.querySelectorAll('.slide');
  const nextBtn = slider.querySelector('.next');
  const prevBtn = slider.querySelector('.prev');

  // Debug check
  console.log("Slider found:", slider);
  console.log("Next button:", nextBtn);
  console.log("Prev button:", prevBtn);

  let index = 0;
  const total = slides.length;

  function showSlide(i) {
    index = (i + total) % total;
    container.style.transform = `translateX(-${index * 100}%)`;
  }

  if (nextBtn) {
    nextBtn.addEventListener('click', () => {
      console.log("NEXT CLICK");
      showSlide(index + 1);
    });
  }

  if (prevBtn) {
    prevBtn.addEventListener('click', () => {
      console.log("PREV CLICK");
      showSlide(index - 1);
    });
  }

  // Optional autoplay
  setInterval(() => showSlide(index + 1), 10000);
});