const tabs=[...document.querySelectorAll('[role="tab"]')];
const descriptions={today:'See who’s working, which shifts need cover and the tasks waiting for a decision. A clear starting point for a busy day.',rota:'Plan the week with approved leave in view. Spot shifts that need cover and find an available teammate before service begins.'};
function selectTab(tab){tabs.forEach(t=>{const active=t===tab;t.setAttribute('aria-selected',String(active));t.tabIndex=active?0:-1});const key=tab.dataset.screen;document.querySelector('#tour-image').src='/assets/'+key+'.webp';document.querySelector('#tour-image').alt=key==='today'?'Today screen: shifts and outstanding tasks':'Rota screen: weekly shifts and cover alerts';document.querySelector('#tour-description').textContent=descriptions[key];document.querySelector('#tour-panel').setAttribute('aria-labelledby',tab.id);document.querySelector('.screen-caption').textContent=key==='today'?'One place to start your day.':'A clearer view of the week ahead.';}
tabs.forEach(tab=>{tab.addEventListener('click',()=>selectTab(tab));tab.addEventListener('keydown',e=>{if(!['ArrowRight','ArrowLeft','Home','End'].includes(e.key))return;e.preventDefault();const i=tabs.indexOf(e.currentTarget);const next=e.key==='Home'?tabs[0]:e.key==='End'?tabs[tabs.length-1]:e.key==='ArrowLeft'?tabs[(i-1+tabs.length)%tabs.length]:tabs[(i+1)%tabs.length];selectTab(next);next.focus()})});
const menu=document.querySelector('.menu-toggle');
menu?.addEventListener('click',()=>{const open=menu.getAttribute('aria-expanded')!=='true';menu.setAttribute('aria-expanded',String(open));menu.setAttribute('aria-label',open?'Close menu':'Open menu');menu.querySelector('span').textContent=open?'−':'+';const nav=document.querySelector('#site-nav');nav.dataset.open=String(open);const scrim=document.querySelector('.nav-scrim');if(scrim)scrim.hidden=!open;document.body.style.overflow=open?'hidden':'';document.documentElement.dataset.navOpen=String(open);if(open){const first=nav.querySelector('a');if(first)first.focus()}else{menu.focus()}});document.querySelector('.nav-scrim')?.addEventListener('click',()=>{if(menu?.getAttribute('aria-expanded')==='true')menu.click()});
document.addEventListener('keydown',event=>{if(event.key==='Escape'&&menu?.getAttribute('aria-expanded')==='true'){menu.click();menu.focus()}});
document.querySelectorAll('[data-billing]').forEach(button=>button.addEventListener('click',()=>{const annual=button.dataset.billing==='annual';document.querySelectorAll('[data-billing]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));document.querySelectorAll('.price[data-monthly]').forEach(price=>{const amount=Number(price.dataset[annual?'annual':'monthly']);price.innerHTML='£'+amount.toLocaleString('en-GB')+'<span>/ '+(annual?'year':'month')+'</span>';price.nextElementSibling.textContent=annual?'12 months paid upfront':'Billed monthly'});document.querySelector('#billing-terms').textContent=annual?'Annual plans are a 12-month commitment, paid upfront. Payments are non-refundable except where the law requires otherwise. All prices exclude VAT.':'Monthly plans have no minimum term. Cancel before your next renewal. All prices exclude VAT.'}));

/* Demo video (.ytlite). Nothing reaches YouTube until the visitor asks: the
   API is warmed on hover/touch so the click itself can start playback with
   sound, the player runs in nocookie mode with every control off, a shield
   swallows pointer events so no YouTube overlay appears, and the player is
   destroyed when the clip ends so the poster comes back instead of an end
   screen. */
(function(){
  var lites=document.querySelectorAll('.ytlite');
  if(!lites.length)return;
  var apiReady=false,apiAsked=false,queue=[];
  function loadAPI(){
    if(apiAsked)return;apiAsked=true;
    var t=document.createElement('script');
    t.src='https://www.youtube.com/iframe_api';
    document.head.appendChild(t);
  }
  window.onYouTubeIframeAPIReady=function(){apiReady=true;queue.forEach(function(fn){fn()});queue=[]};
  function whenReady(fn){if(apiReady)fn();else{queue.push(fn);loadAPI()}}

  lites.forEach(function(el){
    var cover=el.querySelector('.ytlite-cover');
    if(!cover)return;
    var player=null;
    cover.addEventListener('pointerover',loadAPI,{once:true});
    cover.addEventListener('touchstart',loadAPI,{once:true,passive:true});

    cover.addEventListener('click',function(){
      if(player){player.playVideo();return}
      var stage=document.createElement('div');
      stage.className='ytlite-stage';
      var mount=document.createElement('div');
      stage.appendChild(mount);
      var shield=document.createElement('div');
      shield.className='ytlite-shield';
      stage.appendChild(shield);
      el.appendChild(stage);

      whenReady(function(){
        player=new YT.Player(mount,{
          host:'https://www.youtube-nocookie.com',
          videoId:el.getAttribute('data-yt'),
          playerVars:{autoplay:1,controls:0,modestbranding:1,rel:0,playsinline:1,cc_load_policy:0,iv_load_policy:3,disablekb:1,fs:0},
          events:{
            onReady:function(e){e.target.playVideo()},
            onStateChange:function(e){
              if(e.data===YT.PlayerState.PLAYING){el.classList.add('is-playing')}
              else if(e.data===YT.PlayerState.PAUSED){el.classList.remove('is-playing')}
              else if(e.data===YT.PlayerState.ENDED){
                try{player.destroy()}catch(err){}
                player=null;
                if(stage.parentNode)stage.parentNode.removeChild(stage);
                el.classList.remove('is-playing');
              }
            }
          }
        });
        shield.addEventListener('click',function(){
          if(!player||!player.getPlayerState)return;
          var s=player.getPlayerState();
          if(s===YT.PlayerState.PLAYING)player.pauseVideo();else player.playVideo();
        });
      });
    });
  });
})();
