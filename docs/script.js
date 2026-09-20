const button = document.querySelector('.menu-button');
const navigation = document.querySelector('#site-nav');

button?.addEventListener('click', () => {
  const open = navigation.classList.toggle('open');
  button.setAttribute('aria-expanded', String(open));
});

navigation?.addEventListener('click', () => {
  navigation.classList.remove('open');
  button?.setAttribute('aria-expanded', 'false');
});
